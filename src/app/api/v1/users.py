from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import DuplicateValueException, NotFoundException
from ...core.security import ClerkUser, get_current_clerk_user
from ...crud.crud_users import crud_users
from ...models.user import UserCreate, UserRead, UserUpdate, UserUpdateInternal

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
    db_user = await crud_users.get(db=db, schema_to_select=UserRead, id=uuid)
    if not db_user:
        raise NotFoundException("User not found")
    
    return db_user


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
    # Check if user exists by clerk_id
    db_user = await crud_users.get(db=db, schema_to_select=UserRead, clerk_id=clerk_id)
    
    if db_user:
        # Update existing user
        update_data = user_data.model_dump(exclude_unset=True)
        
        # Check if email is being changed and verify it's not already taken
        if "email" in update_data and update_data["email"] and update_data["email"] != db_user["email"]:
            email_row = await crud_users.exists(db=db, email=update_data["email"])
            if email_row:
                raise DuplicateValueException("Email is already registered")
        
        # Ensure clerk_id remains the same
        update_data["clerk_id"] = clerk_id
        
        # If there are no fields to update, return the existing user
        if len(update_data) <= 1:  # Only clerk_id is present
            return db_user
            
        # Create UserUpdateInternal object with updated_at timestamp
        update_obj = UserUpdateInternal(**update_data)
        
        try:
            updated_user = await crud_users.update(
                db=db,
                db_obj=db_user,
                object=update_obj
            )
            return updated_user
        except Exception as e:
            print(f"Error updating user: {e}")
            # If update fails, return the existing user
            return db_user
    else:
        # Create new user
        create_data = user_data.model_dump(exclude_unset=True)
        
        # Ensure required fields are present
        if "name" not in create_data or not create_data.get("name"):
            raise DuplicateValueException("Name is required for new users")
            
        if "email" not in create_data or not create_data.get("email"):
            raise DuplicateValueException("Email is required for new users")
        
        # Check if email is already registered
        email_row = await crud_users.exists(db=db, email=create_data["email"])
        if email_row:
            raise DuplicateValueException("Email is already registered")
        
        # Set clerk_id
        create_data["clerk_id"] = clerk_id
        
        try:
            # Create user without password (clerk handles authentication)
            new_user = await crud_users.create(
                db=db,
                object=UserCreate(**create_data)
            )
            return new_user
        except Exception as e:
            print(f"Error creating user: {e}")
            raise e


# New endpoint to update or create user from Clerk JWT
@router.post("/user/me", response_model=UserRead)
async def update_user_from_clerk(
    request: Request,
    clerk_user: Annotated[ClerkUser, Depends(get_current_clerk_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    user_data: dict[str, Any] = Body(default={})
) -> UserRead:
    """
    Update or create user from Clerk JWT data
    """
    # First check if user exists by clerk_id
    db_user = await crud_users.get(db=db, schema_to_select=UserRead, clerk_id=clerk_user.id)
    
    # If not found by clerk_id, try by email
    if not db_user:
        db_user = await crud_users.get(db=db, schema_to_select=UserRead, email=clerk_user.email)

    if db_user:
        # Update existing user
        update_data = {
            "name": user_data.get("name", clerk_user.name),
            "email": clerk_user.email,  # Always use email from verified JWT
            "profile_image_url": user_data.get("profile_image_url", clerk_user.profile_image_url),
            "clerk_id": clerk_user.id,  # Set clerk_id from JWT
        }

        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        try:
            updated_user = await crud_users.update(
                db=db,
                db_obj=db_user,
                object=UserUpdateInternal(**update_data)
            )
            return updated_user
        except Exception as e:
            print(f"Error updating user: {e}")
            return db_user
    else:
        # Create new user
        create_data = {
            "name": user_data.get("name", clerk_user.name),
            "email": clerk_user.email,
            "profile_image_url": user_data.get("profile_image_url", clerk_user.profile_image_url),
            "clerk_id": clerk_user.id,  # Set clerk_id from JWT
        }

        # Remove None values
        create_data = {k: v for k, v in create_data.items() if v is not None}

        try:
            new_user = await crud_users.create(
                db=db,
                object=UserCreate(**create_data)
            )
            return new_user
        except Exception as e:
            print(f"Error creating user: {e}")
            raise e


