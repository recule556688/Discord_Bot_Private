"""Shared state used across cogs (e.g. temp bans, banned users' roles)."""

from typing import Dict, List

# Store temporary bans with their expiry time
temp_bans = {}

# Store banned users' roles: {user_id: {guild_id: [role_ids]}}
banned_users_roles: Dict[int, Dict[int, List[int]]] = {}
