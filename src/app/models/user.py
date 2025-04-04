from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from ..core.uuid.uuid_types import UserUUID


class UserBase(SQLModel):
    name: str = Field(..., min_length=2, max_length=30, schema_extra={"example": "User Userson"})
    username: str = Field(..., min_length=2, max_length=20, regex="^[a-z0-9]+$", schema_extra={"example": "userson"})
    email: str = Field(..., schema_extra={"example": "user.userson@example.com"})


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(default_factory=UserUUID.create, primary_key=True)  # Primary Key using TypedUUID
    # Override email field from UserBase with additional constraints
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
    last_login: Optional[datetime] = None  # Last login timestamp

    # Metadata Fields
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    is_deleted: bool = Field(default=False)


class UserRead(UserBase):
    id: int
    uuid: str
    email: str
    profile_image_url: str
    role: str
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]
    is_deleted: bool


class UserCreate(UserBase):
    # password: str = Field(..., regex="^.{8,}|[0-9]+|[A-Z]+|[a-z]+|[^a-zA-Z0-9]+$", schema_extra={"example": "Str1ngst!"})

    # @validator('password')
    # def validate_password(cls, value):
    #     if len(value) < 8:
    #         raise ValueError("Password must be at least 8 characters")
    #     return value
    pass


class UserCreateInternal(UserBase):
    # hashed_password: str
    pass


class UserUpdate(SQLModel):
    name: Optional[str] = Field(None, min_length=2, max_length=30)
    username: Optional[str] = Field(None, min_length=2, max_length=20, regex="^[a-z0-9]+$")
    email: Optional[str] = None
    profile_image_url: Optional[str] = None


class UserUpdateInternal(UserUpdate):
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(datetime.UTC))


class UserTierUpdate(SQLModel):
    tier_id: int


class UserDelete(SQLModel):
    is_deleted: bool
    deleted_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))


class UserRestoreDeleted(SQLModel):
    is_deleted: bool
