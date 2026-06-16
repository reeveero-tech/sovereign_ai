"""
NexusCore — مدير المستخدمين
بديل شامل لـ identity/ — إدارة آمنة بدون مراقبة.
"""
import hashlib
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.user.manager")


class Role(Enum):
    MASTER = "master"      # السيد — صلاحيات كاملة
    ADMIN  = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    GUEST  = "guest"


@dataclass
class User:
    user_id: str
    username: str
    email: str
    role: Role
    password_hash: str
    salt: str
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    active: bool = True
    metadata: Dict = field(default_factory=dict)


class UserManager:
    """إدارة المستخدمين بشكل آمن"""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self._username_index: Dict[str, str] = {}  # username → user_id
        logger.info("👥 UserManager initialized")

    def create_user(self, username: str, email: str,
                    password: str, role: Role = Role.ANALYST) -> User:
        if username in self._username_index:
            raise ValueError(f"Username '{username}' already exists")
        salt = os.urandom(32).hex()
        ph   = self._hash(password, salt)
        user = User(
            user_id=uuid.uuid4().hex,
            username=username, email=email,
            role=role, password_hash=ph, salt=salt,
        )
        self.users[user.user_id] = user
        self._username_index[username] = user.user_id
        logger.info(f"👤 User created: {username} ({role.value})")
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        uid  = self._username_index.get(username)
        user = self.users.get(uid) if uid else None
        if not user or not user.active:
            return None
        ph = self._hash(password, user.salt)
        if ph == user.password_hash:
            user.last_login = time.time()
            logger.info(f"✅ Login: {username}")
            return user
        logger.warning(f"❌ Failed login attempt: {username}")
        return None

    def update_role(self, user_id: str, new_role: Role,
                    requested_by: str) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False
        old = user.role.value
        user.role = new_role
        logger.info(f"Role changed: {user.username} {old} → {new_role.value} by {requested_by}")
        return True

    def deactivate(self, user_id: str) -> bool:
        user = self.users.get(user_id)
        if user:
            user.active = False
            logger.info(f"User deactivated: {user.username}")
            return True
        return False

    def get_by_role(self, role: Role) -> List[User]:
        return [u for u in self.users.values() if u.role == role and u.active]

    @staticmethod
    def _hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 200_000
        ).hex()

    def list_users(self) -> List[Dict]:
        return [
            {"id": u.user_id, "username": u.username,
             "email": u.email, "role": u.role.value,
             "active": u.active, "last_login": u.last_login}
            for u in self.users.values()
        ]
