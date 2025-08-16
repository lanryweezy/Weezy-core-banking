from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
# If using JWT tokens, you'd import jose here:
# from jose import JWTError, jwt

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# JWT Token Generation (Example - if we implement token-based auth for APIs)
# These would be moved to a more appropriate place like auth_utils or similar
# and would require python-jose to be installed.
# SECRET_KEY = "YOUR_VERY_SECRET_KEY_HERE" # Should be loaded from config
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.now(timezone.utc) + expires_delta
#     else:
#         expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# def decode_access_token(token: str):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: Optional[str] = payload.get("sub")
#         if username is None:
#             return None # Or raise credential exception
#         return username # Or a TokenData schema object
#     except JWTError:
#         return None # Or raise credential exception

# For API Key generation/verification (if needed for OpenRouter or other services)
# import secrets
# def generate_api_key(length: int = 32) -> str:
#     return secrets.token_hex(length // 2)

# def verify_api_key(provided_key: str, valid_key: str) -> bool:
#     return secrets.compare_digest(provided_key, valid_key)

# Placeholder for OpenRouter interaction - this might involve signing requests or specific auth headers
# This is highly dependent on OpenRouter's specific API requirements
# def get_openrouter_auth_headers():
#     # Example: Load API key from environment/config
#     # open_router_api_key = Config.OPENROUTER_API_KEY
#     # if not open_router_api_key:
#     #     raise ValueError("OpenRouter API key not configured")
#     # return {"Authorization": f"Bearer {open_router_api_key}"}
#     return {} # Placeholder
    pass
