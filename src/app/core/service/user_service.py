from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.crud_users import crud_users
from ...models.user import User, UserCreate, UserRead, UserUpdate, UserUpdateInternal
from ...core.exceptions.http_exceptions import DuplicateValueException, NotFoundException


async def get_user_by_uuid(
    db: AsyncSession,
    uuid: str
) -> UserRead:
    """
    Get a user by UUID.
    
    Args:
        db: Database session
        uuid: User UUID
        
    Returns:
        The user
        
    Raises:
        NotFoundException: If the user is not found
    """
    db_user = await crud_users.get(db=db, schema_to_select=UserRead, id=uuid)
    if not db_user:
        raise NotFoundException("User not found")
    
    return db_user


async def get_user_by_clerk_id(
    db: AsyncSession,
    clerk_id: str
) -> UserRead:
    """
    Get a user by Clerk ID.
    
    Args:
        db: Database session
        clerk_id: Clerk ID
        
    Returns:
        The user
        
    Raises:
        NotFoundException: If the user is not found
    """
    # Use the get method with clerk_id parameter to find the user
    db_user = await crud_users.get(db=db, schema_to_select=UserRead, clerk_id=clerk_id)
    
    if not db_user:
        raise NotFoundException("User not found with the provided Clerk ID")
    
    return db_user


async def create_or_update_user_by_clerk_id(
    db: AsyncSession,
    clerk_id: str,
    user_data: Dict[str, Any]
) -> UserRead:
    """
    Create or update a user based on clerk_id.
    
    Args:
        db: Database session
        clerk_id: Clerk ID
        user_data: User data to create or update
        
    Returns:
        The created or updated user
        
    Raises:
        DuplicateValueException: If the email is already registered
    """
    # Check if user exists by clerk_id
    db_user = await crud_users.get(db=db, schema_to_select=UserRead, clerk_id=clerk_id)
    
    if db_user:
        # Update existing user
        update_data = user_data.copy()
        
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
        
        updated_user = await crud_users.update(
            db=db,
            db_obj=db_user,
            object=update_obj
        )
        return updated_user
    else:
        # Create new user
        create_data = user_data.copy()
        
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
        
        # Create user without password (clerk handles authentication)
        new_user = await crud_users.create(
            db=db,
            object=UserCreate(**create_data)
        )
        return new_user


async def update_user_from_clerk(
    db: AsyncSession,
    clerk_user_data: Dict[str, Any],
    user_data: Dict[str, Any]
) -> UserRead:
    """
    Update or create a user from Clerk JWT data.
    
    Args:
        db: Database session
        clerk_user_data: User data from Clerk JWT
        user_data: Additional user data
        
    Returns:
        The updated or created user
    """
    # First check if user exists by clerk_id
    db_user = await crud_users.get(db=db, schema_to_select=UserRead, clerk_id=clerk_user_data["id"])
    
    # If not found by clerk_id, try by email
    if not db_user:
        db_user = await crud_users.get(db=db, schema_to_select=UserRead, email=clerk_user_data["email"])

    if db_user:
        # Update existing user
        update_data = {
            "name": user_data.get("name", clerk_user_data["name"]),
            "email": clerk_user_data["email"],  # Always use email from verified JWT
            "profile_image_url": user_data.get("profile_image_url", clerk_user_data["profile_image_url"]),
            "clerk_id": clerk_user_data["id"],  # Set clerk_id from JWT
        }

        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        updated_user = await crud_users.update(
            db=db,
            db_obj=db_user,
            object=UserUpdateInternal(**update_data)
        )
        return updated_user
    else:
        # Create new user
        create_data = {
            "name": user_data.get("name", clerk_user_data["name"]),
            "email": clerk_user_data["email"],
            "profile_image_url": user_data.get("profile_image_url", clerk_user_data["profile_image_url"]),
            "clerk_id": clerk_user_data["id"],  # Set clerk_id from JWT
        }

        # Remove None values
        create_data = {k: v for k, v in create_data.items() if v is not None}

        new_user = await crud_users.create(
            db=db,
            object=UserCreate(**create_data)
        )
        return new_user
