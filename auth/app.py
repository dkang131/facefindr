import os, json, logging
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Depends, Response, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt
from jose.exceptions import JWTError
from config import settings
from extensions import hash_password, verify_password
from models import Admin
from database import get_db
from sqlalchemy.orm import Session
import secrets
import traceback

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="auth/templates")

router = APIRouter()

# JWT configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

# Security
security = HTTPBearer()

# Master admin token (in production, this should be stored securely)
MASTER_ADMIN_TOKEN = settings.MASTER_ADMIN_TOKEN

class AdminCreate(BaseModel):
    email: str
    password: str
    role: str = "admin"  # Default role

def verify_master_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to verify master admin access"""
    if credentials.credentials != MASTER_ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access"
        )
    return True

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})

@router.get("/register")
async def register_page(request: Request):
    # Only allow access with master token
    return templates.TemplateResponse("register.html", {"request": request})



@router.post("/register", dependencies=[Depends(verify_master_admin)])
async def register_admin(
    admin_data: AdminCreate, 
    db: Session = Depends(get_db)
):
    """Secure endpoint to register new admins - only accessible with master token"""
    
    try:
        # Check if admin already exists
        existing_admin = db.query(Admin).filter(Admin.email == admin_data.email).first()
        if existing_admin:
            logger.debug(f"Registration attempt failed: Admin with email {admin_data.email} already exists")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Registration failed",
                    "errors": {
                        "code": "EMAIL_EXISTS",
                        "message": "Admin with this email already exists"
                    }
                }
            )
        
        # Hash the password
        try:
            hashed_password = hash_password(admin_data.password)
        except Exception as hash_error:
            logger.error(f"Password hashing error: {str(hash_error)}")
            logger.error(f"Password length: {len(admin_data.password)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Registration failed due to password processing error",
                    "errors": {
                        "code": "PASSWORD_HASH_ERROR",
                        "message": f"Unable to process password: {str(hash_error)}"
                    }
                }
            )
        
        # Create new admin with role
        new_admin = Admin(email=admin_data.email, password=hashed_password, role=admin_data.role)
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        logger.info(f"Admin registered successfully with email: {admin_data.email}")
        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "message": "Admin registered successfully",
                "data": {
                    "admin_id": new_admin.id,
                    "email": new_admin.email,
                    "role": new_admin.role
                }
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Registration failed due to server error",
                "errors": {
                    "code": "SERVER_ERROR",
                    "message": f"An unexpected error occurred during registration: {str(e)}"
                }
            }
        )

@router.post("/login")
async def login_admin(response: Response, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        # Find admin by email
        admin = db.query(Admin).filter(Admin.email == email).first()
        if not admin:
            logger.debug(f"Login attempt failed: User with email {email} not found")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "Login failed",
                    "errors": {
                        "code": "INVALID_CREDENTIALS",
                        "message": "Invalid email or password"
                    }
                }
            )
        
        # Verify password
        try:
            password_valid = verify_password(password, admin.password)
        except Exception as verify_error:
            logger.error(f"Password verification error: {str(verify_error)}")
            logger.error(f"Password length: {len(password)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Login failed due to password verification error",
                    "errors": {
                        "code": "PASSWORD_VERIFY_ERROR",
                        "message": f"Unable to verify password: {str(verify_error)}"
                    }
                }
            )
            
        if not password_valid:
            logger.debug(f"Login attempt failed: Invalid password for email {email}")
            # Check if this might be due to password hash format incompatibility
            if admin.password.startswith("$2") and len(admin.password) > 50:
                logger.warning(f"Possible password hash format incompatibility for user {email}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "message": "Login failed. Please contact administrator to reset your password.",
                        "errors": {
                            "code": "PASSWORD_FORMAT_ERROR",
                            "message": "Password format incompatible. Please contact administrator to reset your password."
                        }
                    }
                )
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "Login failed",
                    "errors": {
                        "code": "INVALID_CREDENTIALS",
                        "message": "Invalid email or password"
                    }
                }
            )
        
        # Create JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + access_token_expires
        to_encode = {"sub": admin.email, "exp": expire}
        try:
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        except Exception as jwt_error:
            logger.error(f"JWT encoding error: {str(jwt_error)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Login failed due to token generation error",
                    "errors": {
                        "code": "JWT_ERROR",
                        "message": f"Unable to generate access token: {str(jwt_error)}"
                    }
                }
            )
        
        logger.info(f"Login successful for email: {email}")
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Login successful",
                "data": {
                    "access_token": encoded_jwt,
                    "token_type": "bearer",
                    "email": admin.email,
                    "role": admin.role
                }
            }
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Login failed due to server error",
                "errors": {
                    "code": "SERVER_ERROR",
                    "message": f"An unexpected error occurred during login: {str(e)}"
                }
            }
        )