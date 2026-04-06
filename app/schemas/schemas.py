from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, field_validator
import re
from app.models.models import AuditActionEnum, RoleEnum


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class UserWithRoleResponse(UserResponse):
    role: RoleEnum


class CreateOrgRequest(BaseModel):
    org_name: str


class OrgResponse(BaseModel):
    org_id: int


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: RoleEnum = RoleEnum.member


class PaginatedUsersResponse(BaseModel):
    total: int
    limit: int
    offset: int
    users: list[UserWithRoleResponse]


class CreateItemRequest(BaseModel):
    item_details: dict[str, Any]


class ItemResponse(BaseModel):
    item_id: int


class ItemDetailResponse(BaseModel):
    id: int
    org_id: int
    created_by: int
    item_details: dict[str, Any]
    created_at: datetime
    model_config = {"from_attributes": True}


class PaginatedItemsResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ItemDetailResponse]


class AuditLogResponse(BaseModel):
    id: int
    org_id: Optional[int]
    actor_id: Optional[int]
    action: AuditActionEnum
    details: dict[str, Any]
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatbotRequest(BaseModel):
    question: str
    stream: bool = False