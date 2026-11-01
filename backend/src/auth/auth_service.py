import os
import re
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import HTTPException, status, Header, Request

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "cage-jwt-secret-key-change-in-production-env-32chars")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# In-memory failed login tracking: ip -> list of timestamps
_FAILED_LOGINS: Dict[str, list] = {}
FAILED_LOGIN_WINDOW_SECONDS = 60
MAX_FAILED_LOGINS_PER_WINDOW = 5


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: int, email: str) -> str:
    """Creates a JWT access token valid for 24 hours."""
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None


def validate_email(email: str) -> bool:
    """Validates basic email format."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip())) if email else False


def validate_password_length(password: str) -> bool:
    """Ensures password length is at least 8 characters."""
    return bool(password and len(password) >= 8)


def record_failed_login(ip: str):
    """Records a failed login attempt for the given IP."""
    now = time.time()
    if ip not in _FAILED_LOGINS:
        _FAILED_LOGINS[ip] = []
    _FAILED_LOGINS[ip].append(now)
    # Prune old timestamps
    _FAILED_LOGINS[ip] = [t for t in _FAILED_LOGINS[ip] if now - t < FAILED_LOGIN_WINDOW_SECONDS]


def is_login_rate_limited(ip: str) -> bool:
    """Returns True if the IP has exceeded 5 failed logins in the last 60 seconds."""
    now = time.time()
    if ip not in _FAILED_LOGINS:
        return False
    valid_attempts = [t for t in _FAILED_LOGINS[ip] if now - t < FAILED_LOGIN_WINDOW_SECONDS]
    _FAILED_LOGINS[ip] = valid_attempts
    return len(valid_attempts) >= MAX_FAILED_LOGINS_PER_WINDOW


def reset_failed_logins(ip: str):
    """Clears failed login attempts for the IP upon successful login."""
    if ip in _FAILED_LOGINS:
        del _FAILED_LOGINS[ip]

