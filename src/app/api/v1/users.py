from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Body, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import DuplicateValueException, NotFoundException
from ...core.service import user_service
from ...models.user import UserRead, UserUpdate

router = APIRouter(tags=["users"])


# New endpoint to get user by UUID (unauthenticated)
@router.get("/user/{uuid}", response_model=UserRead)
async def get_user_by_uuid(
    request: Request,
    uuid: str,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> UserRead:
    """
    Get user by UUID - unauthenticated endpoint
    """
    try:
        # Call the service to handle business logic
        return await user_service.get_user_by_uuid(db=db, uuid=uuid)
    except NotFoundException as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user: {str(e)}"
        )


# New endpoint to create or update user by clerk_id without authentication
@router.post("/user/clerk/{clerk_id}", response_model=UserRead)
async def create_or_update_user_by_clerk_id(
    request: Request,
    clerk_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    user_data: UserUpdate = Body(...)
) -> UserRead:
    """
    Create or update a user based on clerk_id without authentication.
    This endpoint allows for user creation/update without requiring JWT authentication.
    """
    try:
        # Convert Pydantic model to dict for the service layer
        user_data_dict = user_data.model_dump(exclude_unset=True)
        
        # Call the service to handle business logic
        return await user_service.create_or_update_user_by_clerk_id(
            db=db,
            clerk_id=clerk_id,
            user_data=user_data_dict
        )
    except DuplicateValueException as e:
        raise DuplicateValueException(str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating/updating user: {str(e)}"
        )


# New endpoint to update or create user from Clerk JWT
@router.post("/user/me", response_model=UserRead)
async def update_user_from_clerk(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    user_data: dict[str, Any] = Body(default={})
) -> UserRead:
    """
    Update or create user from Clerk JWT data
    
    This endpoint uses the ClerkAuthMiddleware to validate the JWT token
    and attach the clerk_user to request.state
    """
    # Get the clerk_user from request.state (set by middleware)
    if not hasattr(request.state, "clerk_user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
        
    clerk_user = request.state.clerk_user
    
    try:
        # Convert clerk_user to dict for the service layer
        clerk_user_data = {
            "id": clerk_user.id,
            "email": clerk_user.email,
            "name": clerk_user.name,
            "profile_image_url": clerk_user.profile_image_url
        }
        
        # Call the service to handle business logic
        return await user_service.update_user_from_clerk(
            db=db,
            clerk_user_data=clerk_user_data,
            user_data=user_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating/creating user: {str(e)}"
        )


