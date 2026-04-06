from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import (
    get_current_user, require_admin, require_member_or_admin
)
from app.models.models import Membership, User
from app.schemas.schemas import (
    AuditLogResponse, ChatbotRequest, CreateItemRequest,
    CreateOrgRequest, InviteUserRequest, ItemResponse,
    OrgResponse, PaginatedItemsResponse, PaginatedUsersResponse,
    UserWithRoleResponse,
)
from app.services import audit_service, chatbot_service, item_service, org_service

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# Create organization

@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: CreateOrgRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await org_service.create_organization(payload, current_user, db)


#  Invite user

@router.post("/{org_id}/user", status_code=status.HTTP_201_CREATED)
async def invite_user(
    org_id: int,
    payload: InviteUserRequest,
    current_user: User = Depends(get_current_user),
    _: Membership = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await org_service.invite_user(org_id, payload, current_user, db)


#  List users

@router.get("/{org_id}/users", response_model=PaginatedUsersResponse)
async def list_users(
    org_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: Membership = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await org_service.list_org_users(org_id, limit, offset, db)


#  Search users

@router.get("/{org_id}/users/search", response_model=list[UserWithRoleResponse])
async def search_users(
    org_id: int,
    q: str = Query(..., min_length=1),
    _: Membership = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await org_service.search_org_users(org_id, q, db)


# Create item 

@router.post("/{org_id}/item", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    org_id: int,
    payload: CreateItemRequest,
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_member_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await item_service.create_item(org_id, payload, current_user, db)


#  List items 

@router.get("/{org_id}/item", response_model=PaginatedItemsResponse)
async def list_items(
    org_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_member_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await item_service.list_items(
        org_id, limit, offset, current_user, membership, db
    )


#  Audit logs 

@router.get("/{org_id}/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    org_id: int,
    _: Membership = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await audit_service.get_audit_logs(org_id, db)


#  Chatbot 

@router.post("/{org_id}/audit-logs/ask")
async def chatbot_ask(
    org_id: int,
    payload: ChatbotRequest,
    _: Membership = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if payload.stream:
        return StreamingResponse(
            chatbot_service.ask_chatbot_stream(org_id, payload.question, db),
            media_type="text/event-stream",
        )
    answer = await chatbot_service.ask_chatbot(org_id, payload.question, db)
    return {"answer": answer}