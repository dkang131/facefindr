# app/extensions.py
from sqlalchemy.orm import declarative_base
import bcrypt
import logging
import base64
import hashlib

# Set up logging
logger = logging.getLogger(__name__)

# SQLAlchemy Base for models
Base = declarative_base()

# Custom password hashing functions using bcrypt directly
# This avoids passlib compatibility issues

def hash_password(password: str) -> str:
    # Truncate password to 72 bytes to avoid bcrypt limitation
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    try:
        # Generate salt and hash the password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return base64.b64encode(hashed).decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password with bcrypt: {e}")
        # Fallback to SHA-256 with salt if bcrypt fails
        salt = bcrypt.gensalt()
        salt_str = base64.b64encode(salt).decode('utf-8')
        fallback_hash = hashlib.sha256(password_bytes + salt).hexdigest()
        return f"fallback${salt_str}${fallback_hash}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        plain_password_bytes = plain_password.encode('utf-8')
        # Truncate to 72 bytes for bcrypt verification
        if len(plain_password_bytes) > 72:
            plain_password_bytes = plain_password_bytes[:72]
        
        # Check if this is a fallback hash
        if hashed_password.startswith("fallback$"):
            _, salt_str, stored_hash = hashed_password.split('$')
            salt = base64.b64decode(salt_str.encode('utf-8'))
            computed_hash = hashlib.sha256(plain_password_bytes + salt).hexdigest()
            return computed_hash == stored_hash
        
        # Try to decode as base64 (new bcrypt format)
        try:
            hashed_bytes = base64.b64decode(hashed_password.encode('utf-8'))
            return bcrypt.checkpw(plain_password_bytes, hashed_bytes)
        except Exception:
            # If base64 decode fails, it might be an old passlib hash
            # In this case, we'll return False since we can't verify it with our new method
            # The user will need to reset their password
            logger.warning(f"Could not decode password hash. It might be an old passlib hash: {hashed_password[:20]}...")
            return False
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False
