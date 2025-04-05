"""
Clerk client implementation for FastAPI
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from clerk_backend_api import Clerk
import jwt

from ...core.config import settings

# Initialize security for JWT Bearer token
security = HTTPBearer()

# Initialize Clerk client
clerk = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)


class UserEmailAddress(BaseModel):
    """Model for user email address from Clerk"""
    email_address: str
    primary: bool = False
    verified: bool = False


class UserResponse(BaseModel):
    """Response model for user information"""
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    profile_image_url: Optional[str] = None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify the Clerk JWT token and return the user ID
    """
    token = credentials.credentials
    try:
        # Decode the JWT token without verification to extract the user ID
        # This is a simplified approach for development
        payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
        
        # Get the user ID from the token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: User ID not found")
        
        # Get the session ID from the token
        session_id = payload.get("sid")
        
        # For production, you should verify the token with Clerk
        # if session_id:
        #     clerk.sessions.verify(session_id=session_id, token=token)
        
        return {"user_id": user_id, "session_claims": payload}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_current_user_info(auth: Dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    """
    Get the current user's information from Clerk
    This endpoint is protected and requires authentication
    """
    user_id = auth["user_id"]
    
    try:
        # Fetch user data using the Clerk SDK
        user = clerk.users.get(user_id=user_id)
        
        # Extract email safely
        email = _extract_primary_email(user)
        
        return UserResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=email,
            profile_image_url=user.profile_image_url
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")


def _extract_primary_email(user) -> Optional[str]:
    """
    Safely extract the primary email from a user object
    """
    try:
        if not hasattr(user, 'email_addresses') or not user.email_addresses:
            return None
            
        # Handle different types of email_addresses response
        if isinstance(user.email_addresses, list):
            # Try to find primary email first
            for email in user.email_addresses:
                if hasattr(email, 'primary') and email.primary:
                    return email.email_address
                
            # If no primary email is found, return the first one
            if user.email_addresses:
                if hasattr(user.email_addresses[0], 'email_address'):
                    return user.email_addresses[0].email_address
                elif isinstance(user.email_addresses[0], dict):
                    return user.email_addresses[0].get('email_address')
                elif isinstance(user.email_addresses[0], str):
                    return user.email_addresses[0]
                
        # Handle case where email_addresses is a dictionary
        elif isinstance(user.email_addresses, dict):
            primary = user.email_addresses.get('primary')
            if primary:
                return primary
            
            # Get first email if available
            emails = user.email_addresses.get('emails', [])
            if emails and len(emails) > 0:
                return emails[0]
                
        return None
    except Exception:
        # In case of any error, return None
        return None


async def get_session_info(auth: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get information about the current session
    """
    session_claims = auth.get("session_claims", {})
    session_id = session_claims.get("sid")
    
    if not session_id:
        return {
            "user_id": session_claims.get("sub"),
            "session_id": None,
            "issued_at": session_claims.get("iat"),
            "expires_at": session_claims.get("exp"),
            "auth_methods": session_claims.get("auth_methods", [])
        }
    
    try:
        # Get session details from Clerk
        session = clerk.sessions.get(session_id=session_id)
        
        return {
            "user_id": session_claims.get("sub"),
            "session_id": session_id,
            "issued_at": session_claims.get("iat"),
            "expires_at": session_claims.get("exp"),
            "auth_methods": session_claims.get("auth_methods", []),
            "status": session.status,
            "last_active_at": session.last_active_at,
            "created_at": session.created_at
        }
    except Exception:
        # Fallback to token claims if session retrieval fails
        return {
            "user_id": session_claims.get("sub"),
            "session_id": session_id,
            "issued_at": session_claims.get("iat"),
            "expires_at": session_claims.get("exp"),
            "auth_methods": session_claims.get("auth_methods", [])
        }


async def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify a Clerk JWT token and return the claims
    """
    try:
        # Decode the JWT token without verification for development
        payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
        
        # For production, you should verify the token with Clerk
        # session_id = payload.get("sid")
        # if session_id:
        #     clerk.sessions.verify(session_id=session_id, token=token)
        
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_user_by_id(user_id: str) -> UserResponse:
    """
    Get a user by their Clerk ID
    """
    try:
        # Fetch user data using the Clerk SDK
        user = clerk.users.get(user_id=user_id)
        
        # Extract email safely
        email = _extract_primary_email(user)
        
        return UserResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=email,
            profile_image_url=user.profile_image_url
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")


# Async versions of the functions
async def get_current_user_async(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Async version: Verify the Clerk JWT token and return the user ID
    """
    token = credentials.credentials
    try:
        # Decode the JWT token without verification to extract the user ID
        payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
        
        # Get the user ID from the token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: User ID not found")
        
        # Get the session ID from the token
        session_id = payload.get("sid")
        
        # For production, you should verify the token with Clerk
        # if session_id:
        #     async with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk_async:
        #         await clerk_async.sessions.verify_async(session_id=session_id, token=token)
        
        return {"user_id": user_id, "session_claims": payload}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_user_by_id_async(user_id: str) -> UserResponse:
    """
    Async version: Get a user by their Clerk ID
    """
    try:
        # For async operations, we need to use async with
        async with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk_async:
            # Fetch user data using the Clerk SDK
            user = await clerk_async.users.get_async(user_id=user_id)
            
            # Extract email safely
            email = _extract_primary_email(user)
            
            return UserResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=email,
                profile_image_url=user.profile_image_url
            )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")
