from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ...crud.crud_organizations import crud_organizations
from ...crud.crud_users import crud_users
from ...models.organization import Organization, OrganizationCreate, OrganizationRead, OrganizationUpdate, OrganizationUpdateInternal
from ...models.user import User, UserRead, UserUpdate
from ...core.exceptions.http_exceptions import DuplicateValueException, NotFoundException


async def create_organization(
    db: AsyncSession,
    id: str,
    organization_data: OrganizationCreate
) -> OrganizationRead:
    """
    Create a new organization and associate it with the user.
    
    Args:
        db: Database session
        user_id: ID of the user creating the organization
        organization_data: Organization data to create
        
    Returns:
        The created organization
        
    Raises:
        DuplicateValueException: If the user already has an organization or the org_url is taken
        NotFoundException: If the user is not found
    """
    # Get the user from the database by uuid using direct query
    import logging
    from sqlmodel import select as sqlmodel_select
    from ...models.user import User
    
    logging.info(f"Looking for user with uuid: {id}")
    stmt = sqlmodel_select(User).where(User.id == id).limit(1)
    result = await db.execute(stmt)
    db_user_tuple = result.first()
    
    if not db_user_tuple:
        raise NotFoundException("User not found")
        
    # Extract the user from the tuple
    db_user = db_user_tuple[0]
    
    # Check if the user already has an organization
    if db_user.organization_id:
        # Get the organization details using direct query
        org_stmt = sqlmodel_select(Organization).where(Organization.id == db_user.organization_id).limit(1)
        org_result = await db.execute(org_stmt)
        org_tuple = org_result.first()
        
        if org_tuple:
            existing_org = org_tuple[0]
            raise DuplicateValueException(
                f"User is already associated to an organization: {existing_org.name}"
            )
    
    # Create the organization
    new_organization = await crud_organizations.create(
        db=db,
        object=organization_data
    )
    
    # Associate the user with the organization directly
    # Update the user's organization_id and set role to admin
    db_user.organization_id = new_organization.id
    db_user.role = "admin"  # Make the organization creator an admin
    
    # Commit the changes to the database
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    logging.info(f"Updated user {db_user.id} with organization_id {new_organization.id} and role 'admin'")
    
    return new_organization


async def get_organization_by_user_id(
    db: AsyncSession,
    user_id: str
) -> OrganizationRead:
    """
    Get the organization associated with a user.
    
    Args:
        db: Database session
        user_id: ID of the user
        
    Returns:
        The organization
        
    Raises:
        NotFoundException: If the user doesn't have an organization
    """
    # Get the user from the database by clerk_id
    # The user_id from clerk_user.id is actually the clerk_id, not the database id
    import logging
    logging.info(f"Looking for user with clerk_id: {user_id}")
    db_user = await crud_users.get(db=db, schema_to_select=None, clerk_id=user_id)
    if not db_user:
        raise NotFoundException("User not found")
    
    # Check if the user has an organization
    if not db_user.organization_id:
        raise NotFoundException("User does not have an organization")
    
    # Get the organization details
    organization = await crud_organizations.get(db=db, schema_to_select=OrganizationRead, id=db_user.organization_id)
    if not organization:
        raise NotFoundException("Organization not found")
    
    return organization


async def update_organization(
    db: AsyncSession,
    user_id: str,
    organization_data: OrganizationUpdate
) -> OrganizationRead:
    """
    Update the organization associated with a user.
    
    Args:
        db: Database session
        user_id: ID of the user
        organization_data: Organization data to update
        
    Returns:
        The updated organization
        
    Raises:
        NotFoundException: If the user doesn't have an organization
        DuplicateValueException: If the org_url is already taken
    """
    # Get the user from the database by clerk_id
    # The user_id from clerk_user.id is actually the clerk_id, not the database id
    import logging
    logging.info(f"Looking for user with clerk_id: {user_id}")
    db_user = await crud_users.get(db=db, schema_to_select=None, clerk_id=user_id)
    if not db_user:
        raise NotFoundException("User not found")
    
    # Check if the user has an organization
    if not db_user.organization_id:
        raise NotFoundException("User does not have an organization")
    
    # Get the organization
    db_organization = await crud_organizations.get(db=db, schema_to_select=None, id=db_user.organization_id)
    if not db_organization:
        raise NotFoundException("Organization not found")
    
    # Update the organization
    update_data = organization_data.model_dump(exclude_unset=True)
    if not update_data:
        return await crud_organizations.get(db=db, schema_to_select=OrganizationRead, id=db_user.organization_id)
    
    # If org_url is being updated, check if it's already taken by another organization
    if "org_url" in update_data and update_data["org_url"]:
        existing_org = await crud_organizations.exists(
            db=db, 
            org_url=update_data["org_url"],
            id__ne=db_user.organization_id  # Exclude current organization from check
        )
        if existing_org:
            raise DuplicateValueException(f"Organization URL '{update_data['org_url']}' is already taken")
        
    updated_organization = await crud_organizations.update(
        db=db,
        db_obj=db_organization,
        object=OrganizationUpdateInternal(**update_data)
    )
    return updated_organization


async def list_organization_users(
    db: AsyncSession,
    user_id: str
) -> List[UserRead]:
    """
    List all users in the same organization as the specified user.
    
    Args:
        db: Database session
        user_id: ID of the user
        
    Returns:
        List of users in the organization
        
    Raises:
        NotFoundException: If the user doesn't have an organization
    """
    # Get the user from the database by clerk_id
    # The user_id from clerk_user.id is actually the clerk_id, not the database id
    import logging
    logging.info(f"Looking for user with clerk_id: {user_id}")
    db_user = await crud_users.get(db=db, schema_to_select=None, clerk_id=user_id)
    if not db_user:
        raise NotFoundException("User not found")
    
    # Check if the user has an organization
    if not db_user.organization_id:
        raise NotFoundException("User does not have an organization")
    
    # Query all users with the same organization_id
    statement = select(User).where(
        User.organization_id == db_user.organization_id,
        User.is_deleted == False  # Exclude deleted users
    )
    result = await db.execute(statement)
    users = result.scalars().all()
    
    # Convert to UserRead model
    return [UserRead.model_validate(user) for user in users]
