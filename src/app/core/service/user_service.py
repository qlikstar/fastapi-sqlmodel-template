from typing import Any, Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.crud_users import crud_users
from ...models.user import User, UserCreate, UserRead, UserUpdate, UserUpdateInternal
from ...core.exceptions.http_exceptions import DuplicateValueException, NotFoundException, BadRequestException


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
    # Use a more specific query to get a single user by clerk_id
    from sqlalchemy import select
    from sqlmodel import select as sqlmodel_select
    from ...models.user import User
    
    # First try to find a single user with this clerk_id including organization relationship
    stmt = sqlmodel_select(User).where(User.clerk_id == clerk_id).limit(1)
    result = await db.execute(stmt)
    db_user_tuple = result.first()
    
    # Convert tuple to User object if found
    db_user = db_user_tuple[0] if db_user_tuple else None
    
    # If user exists, refresh it to get the latest data including organization
    if db_user:
        await db.refresh(db_user)
    
    if db_user:
        # Update existing user
        update_data = user_data.copy()
        
        # Check if email is being changed and verify it's not already taken
        if "email" in update_data and update_data["email"] and update_data["email"] != db_user.email:
            # Use a direct query to check if email exists
            email_stmt = sqlmodel_select(User).where(User.email == update_data["email"]).where(User.id != db_user.id)
            email_result = await db.execute(email_stmt)
            email_row_tuple = email_result.first()
            if email_row_tuple:
                raise DuplicateValueException("Email is already registered")
        
        # Ensure clerk_id remains the same
        update_data["clerk_id"] = clerk_id
        
        # If there are no fields to update, return the existing user
        if len(update_data) <= 1:  # Only clerk_id is present
            return db_user
            
        # Create UserUpdateInternal object with updated_at timestamp
        update_obj = UserUpdateInternal(**update_data)
        update_data = update_obj.dict(exclude_unset=True)  # Get only the updated fields
        
        # Update the user directly
        for key, value in update_data.items():
            setattr(db_user, key, value)
        
        # Set updated_at timestamp
        db_user.updated_at = datetime.now().replace(tzinfo=None)
        
        # Commit the changes
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        return db_user
    else:
        # Create new user
        create_data = user_data.copy()
        
        # Ensure required fields are present
        if "first_name" not in create_data or not create_data.get("first_name"):
            raise BadRequestException("First name is required for new users")
            
        if "last_name" not in create_data or not create_data.get("last_name"):
            raise BadRequestException("Last name is required for new users")
            
        if "email" not in create_data or not create_data.get("email"):
            raise BadRequestException("Email is required for new users")
        
        # Check if email is already registered using direct query
        email_stmt = sqlmodel_select(User).where(User.email == create_data["email"])
        email_result = await db.execute(email_stmt)
        email_row_tuple = email_result.first()
        if email_row_tuple:
            raise DuplicateValueException("Email is already registered")
        
        # Set clerk_id
        create_data["clerk_id"] = clerk_id
        
        # Create user directly
        new_user = User(**create_data)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        return new_user


async def update_user_from_clerk(
    db: AsyncSession,
    clerk_user_data: Dict[str, Any],
    user_data: Dict[str, Any]
) -> UserRead:
    import logging
    logging.info(f"update_user_from_clerk called with clerk_user_data: {clerk_user_data}")
    logging.info(f"Checking if user exists in database with clerk_id: {clerk_user_data['id']}")
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
    try:
        logging.info(f"Looking for user with clerk_id: {clerk_user_data['id']}")
        db_user = await crud_users.get(db=db, schema_to_select=UserRead, clerk_id=clerk_user_data["id"])
        logging.info(f"Result of get by clerk_id: {db_user}")
    except Exception as e:
        import traceback
        logging.error(f"Error getting user by clerk_id: {str(e)}")
        logging.error(traceback.format_exc())
        raise
    
    # If not found by clerk_id, try by email
    if not db_user:
        try:
            logging.info(f"Looking for user with email: {clerk_user_data['email']}")
            db_user = await crud_users.get(db=db, schema_to_select=UserRead, email=clerk_user_data["email"])
            logging.info(f"Result of get by email: {db_user}")
        except Exception as e:
            import traceback
            logging.error(f"Error getting user by email: {str(e)}")
            logging.error(traceback.format_exc())
            raise

    if db_user:
        # Update existing user
        # Get first_name and last_name from user_data or clerk_user_data
        first_name = user_data.get("first_name", clerk_user_data.get("first_name", ""))
        last_name = user_data.get("last_name", clerk_user_data.get("last_name", ""))
        
        update_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": clerk_user_data["email"],  # Always use email from verified JWT
            "profile_image_url": user_data.get("profile_image_url", clerk_user_data.get("profile_image_url")),
            "clerk_id": clerk_user_data["id"],  # Set clerk_id from JWT
        }

        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        try:
            logging.info(f"Updating existing user with ID: {db_user.id} and data: {update_data}")
            updated_user = await crud_users.update(
                db=db,
                db_obj=db_user,
                object=UserUpdateInternal(**update_data)
            )
            logging.info(f"User updated successfully: {updated_user}")
            logging.info(f"Database operation: UPDATE user SET first_name='{update_data.get('first_name')}', last_name='{update_data.get('last_name')}' WHERE id='{db_user.id}'")
        except Exception as e:
            import traceback
            logging.error(f"Error updating user: {str(e)}")
            logging.error(traceback.format_exc())
            raise
        return updated_user
    else:
        # Create new user
        # Get first_name and last_name from user_data or clerk_user_data
        first_name = user_data.get("first_name", clerk_user_data.get("first_name", ""))
        last_name = user_data.get("last_name", clerk_user_data.get("last_name", ""))
        
        create_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": clerk_user_data["email"],
            "profile_image_url": user_data.get("profile_image_url", clerk_user_data.get("profile_image_url")),
            "clerk_id": clerk_user_data["id"],  # Set clerk_id from JWT
        }

        # Remove None values
        create_data = {k: v for k, v in create_data.items() if v is not None}

        try:
            logging.info(f"Creating new user with data: {create_data}")
            new_user = await crud_users.create(
                db=db,
                object=UserCreate(**create_data)
            )
            logging.info(f"User created successfully with ID: {new_user.id}")
            logging.info(f"Database operation: INSERT INTO user (id, clerk_id, first_name, last_name, email, profile_image_url) VALUES ('{new_user.id}', '{create_data.get('clerk_id')}', '{create_data.get('first_name')}', '{create_data.get('last_name')}', '{create_data.get('email')}', '{create_data.get('profile_image_url')}')")
            return new_user
        except Exception as e:
            import traceback
            logging.error(f"Error creating user: {str(e)}")
            logging.error(traceback.format_exc())
            raise
