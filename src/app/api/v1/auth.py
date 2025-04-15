"""
Authentication endpoints using Clerk
"""
import logging
import jwt
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ...core.clerk.client import (
    get_current_user_info,
    get_session_info,
    get_user_by_id,
    UserResponse
)
from ...core.security import CLERK_PUBLIC_KEY

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=UserResponse)
async def get_me(user_info: UserResponse = Depends(get_current_user_info)):
    """
    Get the current user's information from Clerk
    This endpoint is protected and requires authentication
    """
    return user_info


@router.get("/auth/session")
async def get_session(session: Dict[str, Any] = Depends(get_session_info)):
    """
    Get information about the current session
    This endpoint is protected and requires authentication
    """
    return session


# Temporary endpoint for testing - REMOVE IN PRODUCTION
@router.get("/auth/debug-token")
async def debug_token(request: Request):
    """
    Debug endpoint to print JWT token and extract user ID
    This is for testing purposes only and should be removed in production
    """
    # Get the authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    # Extract the token
    token = auth_header.split(" ")[1]
    
    try:
        # Decode the token without verification for debugging purposes
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        # Extract user ID (sub claim)
        user_id = decoded_token.get("sub")
        
        # Log the token and user ID
        logging.info(f"JWT Token: {token}")
        logging.info(f"User ID: {user_id}")
        
        # Print to console for immediate visibility
        print(f"\n==== DEBUG TOKEN INFO ====")
        print(f"JWT Token: {token}")
        print(f"User ID: {user_id}")
        print(f"==== END DEBUG INFO ====\n")
        
        # Return basic token info
        return {
            "user_id": user_id,
            "token_info": {
                "issued_at": decoded_token.get("iat"),
                "expires_at": decoded_token.get("exp"),
                "issuer": decoded_token.get("iss")
            }
        }
    except Exception as e:
        logging.error(f"Error decoding token: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error decoding token: {str(e)}")
# @router.get("/auth/test/users/{clerk_id}", response_model=UserResponse)
# async def test_get_user_by_clerk_id(clerk_id: str):
#     """
#     Temporary endpoint for testing purposes.
#     Get a user by their Clerk ID without authentication.
    
#     WARNING: This endpoint should be removed in production as it exposes
#     user data without authentication.
#     """
#     try:
#         return await get_user_by_id(clerk_id)
#     except Exception as e:
#         raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")
