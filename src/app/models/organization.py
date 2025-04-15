from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from src.app.core.uuid.uuid_types import OrgUUID
from .user import User


class Organization(SQLModel, table=True):
    """Organization model for storing organization data."""
    id: str = Field(default_factory=OrgUUID.create, primary_key=True)
    name: str = Field(..., min_length=2, max_length=100, schema_extra={"example": "Acme Corporation"})
    org_url: Optional[str] = Field(default=None, index=True, schema_extra={"example": "acme-corp"})
    
    # Metadata Fields
    created_at: datetime = Field(default_factory=lambda: datetime.now().replace(tzinfo=None))
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    is_deleted: bool = Field(default=False)
    
    # Relationships
    users: list["User"] = Relationship(back_populates="organization")


# Add the relationship to User model
User.update_forward_refs()


class OrganizationRead(SQLModel):
    """Schema for reading organization data."""
    id: str
    name: str
    org_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False


class OrganizationCreate(SQLModel):
    """Schema for creating a new organization."""
    name: str = Field(..., min_length=2, max_length=100, schema_extra={"example": "Acme Corporation"})
    org_url: Optional[str] = Field(None, schema_extra={"example": "acme-corp"})


class OrganizationUpdate(SQLModel):
    """Schema for updating an organization."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    org_url: Optional[str] = None


class OrganizationUpdateInternal(OrganizationUpdate):
    """Schema for internal organization updates with timestamp."""
    updated_at: datetime = Field(default_factory=lambda: datetime.now().replace(tzinfo=None))


class OrganizationDelete(SQLModel):
    """Schema for soft-deleting an organization."""
    is_deleted: bool = True
    deleted_at: datetime = Field(default_factory=lambda: datetime.now().replace(tzinfo=None))
