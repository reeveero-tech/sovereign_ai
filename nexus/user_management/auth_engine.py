"""
NexusCore — محرك المصادقة
JWT tokens + session management (بدون مراقبة).
"""
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.user.auth")


@dataclass
class Session:
    session_id: str
    user_id: str
    username: str
    role: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 86400)
    ip_address: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class AuthEngine:
    """محرك مصادقة آمن مع JWT-like tokens"""

    def __init__(self, secret: Optional[str] = None):
        self._secret = secret or os.urandom(32).hex()
        self.sessions: Dict[str, Session] = {}
        self._failed_attempts: Dict[str, List[float]] = {}
        self.MAX_ATTEMPTS = 5
        self.LOCKOUT_SECONDS = 300
        logger.info("🔑 AuthEngine initialized")

    def create_token(self, user_id: str, username: str,
                     role: str, ip: Optional[str] = None,
                     ttl: int = 86400) -> str:
        import uuid
        session_id = uuid.uuid4().hex
        session = Session(
            session_id=session_id, user_id=user_id,
            username=username, role=role,
            expires_at=time.time() + ttl,
            ip_address=ip,
        )
        self.sessions[session_id] = session
        payload = json.dumps({"sid": session_id, "uid": user_id,
                              "role": role, "exp": session.expires_at})
        sig = self._sign(payload)
        import base64
        token = base64.urlsafe_b64encode(
            f"{payload}.{sig}".encode()
        ).decode()
        return token

    def verify_token(self, token: str) -> Optional[Session]:
        try:
            import base64
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            payload_str, sig = decoded.rsplit(".", 1)
            if not hmac.compare_digest(sig, self._sign(payload_str)):
                return None
            payload = json.loads(payload_str)
            session = self.sessions.get(payload["sid"])
            if session and not session.is_expired:
                return session
            return None
        except Exception:
            return None

    def revoke_token(self, token: str) -> bool:
        session = self.verify_token(token)
        if session:
            self.sessions.pop(session.session_id, None)
            return True
        return False

    def is_locked_out(self, username: str) -> bool:
        now = time.time()
        attempts = [t for t in self._failed_attempts.get(username, [])
                    if now - t < self.LOCKOUT_SECONDS]
        self._failed_attempts[username] = attempts
        return len(attempts) >= self.MAX_ATTEMPTS

    def record_failed_attempt(self, username: str) -> None:
        self._failed_attempts.setdefault(username, []).append(time.time())
        count = len(self._failed_attempts[username])
        if count >= self.MAX_ATTEMPTS:
            logger.warning(f"🔒 Account locked: {username} ({count} failed attempts)")

    def cleanup_expired(self) -> int:
        expired = [sid for sid, s in self.sessions.items() if s.is_expired]
        for sid in expired:
            del self.sessions[sid]
        return len(expired)

    def _sign(self, payload: str) -> str:
        return hmac.new(
            self._secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    def get_active_sessions(self) -> List[Dict]:
        now = time.time()
        return [
            {"session_id": s.session_id, "username": s.username,
             "role": s.role, "expires_in": round(s.expires_at - now, 0),
             "ip": s.ip_address}
            for s in self.sessions.values() if not s.is_expired
        ]
