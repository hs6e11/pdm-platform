# backend/middleware/enterprise_auth.py
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
import bcrypt
from typing import Optional, List

class EnterpriseAuth:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.security = HTTPBearer()
        
    async def create_access_token(self, user_data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = user_data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
            
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm="HS256")
        return encoded_jwt
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """Verify JWT token"""
        try:
            payload = jwt.decode(credentials.credentials, self.secret_key, algorithms=["HS256"])
            user_id: str = payload.get("sub")
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
                
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

class RoleBasedAccess:
    def __init__(self):
        self.permissions = {
            'admin': [
                'read:all', 'write:all', 'delete:all',
                'manage:users', 'manage:clients', 'manage:machines'
            ],
            'client_admin': [
                'read:own_client', 'write:own_client',
                'manage:own_machines', 'manage:own_users'
            ],
            'operator': [
                'read:assigned_machines', 'write:maintenance_logs'
            ],
            'viewer': [
                'read:assigned_machines'
            ]
        }
    
    def check_permission(self, user_role: str, required_permission: str) -> bool:
        """Check if user role has required permission"""
        user_permissions = self.permissions.get(user_role, [])
        return required_permission in user_permissions or 'write:all' in user_permissions
    
    def require_permission(self, permission: str):
        """Decorator to require specific permission"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Get user from token (assumes token verification middleware)
                user = kwargs.get('current_user')
                if not user:
                    raise HTTPException(status_code=401, detail="Authentication required")
                
                if not self.check_permission(user.get('role'), permission):
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
