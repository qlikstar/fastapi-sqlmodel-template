from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from ..core.uuid.uuid_types import UserUUID

if TYPE_CHECKING:
    from .organization import Organization


class User(SQLModel, table=True):
    id: str = Field(default_factory=UserUUID.create, primary_key=True)  # Primary Key using TypedUUID
    clerk_id: Optional[str] = Field(default=None, index=True, unique=True)
    first_name: str = Field(default="", min_length=0, max_length=30, schema_extra={"example": "Mike"})
    last_name: str = Field(default="", min_length=0, max_length=30, schema_extra={"example": "Tyson"})
    
    # Property to get full name
    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    email: str = Field(
        ...,
        unique=True,
        index=True,
        nullable=False,
        schema_extra={"example": "user.userson@example.com"}
    )
    profile_image_url: str = Field(default="https://www.profileimageurl.com")

    # Custom Application Fields
    role: str = Field(default="user")  # 'user', 'admin', etc.
    is_active: bool = Field(default=True)  # User status flag
    
    # Organization relationship
    organization_id: Optional[str] = Field(default=None, foreign_key="organization.id")
    organization: Optional["Organization"] = Relationship(back_populates="users")

    # Metadata Fields
    created_at: datetime = Field(default_factory=lambda: datetime.now().replace(tzinfo=None))
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    is_deleted: bool = Field(default=False)


class UserRead(SQLModel):
    id: str
    clerk_id: Optional[str]
    first_name: str = Field(default="", min_length=0, max_length=30, schema_extra={"example": "Mike"})
    last_name: str = Field(default="", min_length=0, max_length=30, schema_extra={"example": "Tyson"})
    
    # Property to get full name
    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    email: str = Field(..., schema_extra={"example": "user.userson@example.com"})
    profile_image_url: str
    role: str
    is_active: bool
    organization_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]
    is_deleted: bool


class UserCreate(SQLModel):
    first_name: str = Field(default="", min_length=0, max_length=30, schema_extra={"example": "User"})
    last_name: str = Field(default="", min_length=0, max_length=30, schema_extra={"example": "Userson"})
    email: str = Field(..., schema_extra={"example": "user.userson@example.com"})
    clerk_id: Optional[str] = None
    profile_image_url: Optional[str] = None


class UserCreateInternal(SQLModel):
    first_name: str = Field(default="", min_length=0, max_length=30, schema_extra={"example": "User"})
    last_name: str = Field(default="", min_length=0, max_length=30, schema_extra={"example": "Userson"})
    email: str = Field(..., schema_extra={"example": "user.userson@example.com"})
    clerk_id: Optional[str] = None


class UserUpdate(SQLModel):
    first_name: Optional[str] = Field(None, min_length=0, max_length=30)
    last_name: Optional[str] = Field(None, min_length=0, max_length=30)
    email: Optional[str] = None
    profile_image_url: Optional[str] = None


class UserUpdateInternal(UserUpdate):
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now().replace(tzinfo=None))


class UserTierUpdate(SQLModel):
    tier_id: int


class UserDelete(SQLModel):
    is_deleted: bool
    deleted_at: datetime = Field(default_factory=lambda: datetime.now().replace(tzinfo=None))


class UserRestoreDeleted(SQLModel):
    is_deleted: bool
