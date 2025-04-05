"""
Authentication endpoints using Clerk
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException

from ...core.clerk.client import (
    get_current_user_info,
    get_session_info,
    get_user_by_id,
    UserResponse
)

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
