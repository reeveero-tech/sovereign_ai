"""
NexusCore — مدير الملفات الشخصية
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.user.profile")


@dataclass
class Profile:
    user_id: str
    display_name: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    bio: str = ""
    avatar_url: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class ProfileManager:
    """يدير الملفات الشخصية للمستخدمين"""

    def __init__(self):
        self.profiles: Dict[str, Profile] = {}
        logger.info("📝 ProfileManager initialized")

    def create_profile(self, user_id: str, display_name: str,
                       preferences: Optional[Dict] = None) -> Profile:
        profile = Profile(user_id=user_id, display_name=display_name,
                          preferences=preferences or {})
        self.profiles[user_id] = profile
        return profile

    def get_profile(self, user_id: str) -> Optional[Profile]:
        return self.profiles.get(user_id)

    def update_preference(self, user_id: str, key: str, value: Any) -> bool:
        p = self.profiles.get(user_id)
        if p:
            p.preferences[key] = value
            p.updated_at = time.time()
            return True
        return False

    def update_display_name(self, user_id: str, name: str) -> bool:
        p = self.profiles.get(user_id)
        if p:
            p.display_name = name
            p.updated_at = time.time()
            return True
        return False

    def add_tag(self, user_id: str, tag: str) -> bool:
        p = self.profiles.get(user_id)
        if p and tag not in p.tags:
            p.tags.append(tag)
            return True
        return False

    def search_by_tag(self, tag: str) -> List[Profile]:
        return [p for p in self.profiles.values() if tag in p.tags]

    def to_dict(self, profile: Profile) -> Dict:
        return {
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "preferences": profile.preferences,
            "tags": profile.tags,
            "bio": profile.bio,
            "avatar_url": profile.avatar_url,
        }
