"""
Authentication endpoints using Clerk
"""
import logging
from typing import Dict, Any, Union, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...core.clerk.client import (
    get_session_info,
)
from ...models.user import UserRead

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=UserRead)
async def get_me(
    request: Request
):
    """
    Get the current user's information from the database
    This endpoint is protected and requires authentication
    
    Returns:
        Complete user information from the database
        
    Raises:
        HTTPException: If the user is not authenticated or not found in the database
    """
    # Check if db_user is in request.state (set by middleware)
    if hasattr(request.state, "db_user") and request.state.db_user is not None:
        logging.info("Using db_user from request.state")
        return request.state.db_user
    
    # If db_user is not in request.state, return unauthorized
    logging.warning("No db_user found in request.state, returning unauthorized")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )


@router.get("/auth/session")
async def get_session(session: Dict[str, Any] = Depends(get_session_info)):
    """
    Get information about the current session
    This endpoint is protected and requires authentication
    """
    return session

