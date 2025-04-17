from typing import Annotated, List
import logging
import traceback
import sys

# Configure root logger to output to stderr
root_logger = logging.getLogger()
if not root_logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

from fastapi import APIRouter, Depends, Request, Body, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import DuplicateValueException, NotFoundException
from ...core.service import organization_service
from ...models.organization import OrganizationCreate, OrganizationRead, OrganizationUpdate
from ...models.user import UserRead

router = APIRouter(tags=["organizations"])


@router.post("/organization", response_model=OrganizationRead)
async def create_organization(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    organization_data: OrganizationCreate = Body(...)
) -> OrganizationRead:
    """
    Create a new organization for the authenticated user.
    
    - Only authenticated users can create an organization
    - A user can only be associated with one organization
    - The user creating the organization becomes associated with it
    - Optional org_url can be provided for a custom URL slug
    """
    # Get the authenticated user from request state (set by middleware)
    if not hasattr(request.state, "db_user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to create an organization"
        )
    
    # Validate and extract user ID
    db_user = request.state.db_user
    logging.info(f"Creating organization for user: {db_user}")
    
    try:
        # Log the user ID and organization data
        logging.info(f"User ID: {db_user.id}, Organization data: {organization_data}")
        
        # Call the service to handle business logic
        result = await organization_service.create_organization(
            db=db,
            id=db_user.id,
            organization_data=organization_data
        )
        logging.info(f"Organization created successfully: {result}")
        return result
    except DuplicateValueException as e:
        raise DuplicateValueException(str(e))
    except NotFoundException as e:
        raise NotFoundException(str(e))
    except Exception as e:
        logging.error(f"Error creating organization: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating organization: {str(e)}"
        )


@router.get("/organization/me", response_model=OrganizationRead)
async def get_my_organization(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> OrganizationRead:
    """
    Get the organization associated with the authenticated user.
    """
    # Get the authenticated user from request state (set by middleware)
    if not hasattr(request.state, "clerk_user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to get organization"
        )
    
    # Validate and extract user ID
    clerk_user = request.state.clerk_user
    
    try:
        # Call the service to handle business logic
        return await organization_service.get_organization_by_user_id(
            db=db,
            user_id=clerk_user.id
        )
    except NotFoundException as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting organization: {str(e)}"
        )


@router.put("/organization/me", response_model=OrganizationRead)
async def update_my_organization(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    organization_data: OrganizationUpdate = Body(...)
) -> OrganizationRead:
    """
    Update the organization associated with the authenticated user.
    """
    # Get the authenticated user from request state (set by middleware)
    if not hasattr(request.state, "clerk_user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to update organization"
        )
    
    # Validate and extract user ID
    clerk_user = request.state.clerk_user
    
    try:
        # Call the service to handle business logic
        return await organization_service.update_organization(
            db=db,
            user_id=clerk_user.id,
            organization_data=organization_data
        )
    except DuplicateValueException as e:
        raise DuplicateValueException(str(e))
    except NotFoundException as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating organization: {str(e)}"
        )


@router.get("/organization/users", response_model=List[UserRead])
async def list_organization_users(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> List[UserRead]:
    """
    List all users under the authenticated user's organization.
    
    - Only authenticated users can access this endpoint
    - All users within the same organization can see the list of users
    - Returns a list of users with their basic information
    """
    # Get the authenticated user from request state (set by middleware)
    if not hasattr(request.state, "clerk_user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to list organization users"
        )
    
    # Validate and extract user ID
    clerk_user = request.state.clerk_user
    
    try:
        # Call the service to handle business logic
        return await organization_service.list_organization_users(
            db=db,
            user_id=clerk_user.id
        )
    except NotFoundException as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing organization users: {str(e)}"
        )
