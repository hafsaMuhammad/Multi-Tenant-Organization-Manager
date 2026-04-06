from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditActionEnum, AuditLog, Item, Membership, RoleEnum, User
from app.schemas.schemas import (
    CreateItemRequest, ItemDetailResponse, ItemResponse, PaginatedItemsResponse
)


async def create_item(
    org_id: int,
    payload: CreateItemRequest,
    current_user: User,
    db: AsyncSession,
) -> ItemResponse:
    item = Item(
        org_id=org_id,
        created_by=current_user.id,
        item_details=payload.item_details,
    )
    db.add(item)
    await db.flush()

    db.add(AuditLog(
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditActionEnum.item_created,
        details={"item_id": item.id, "item_details": payload.item_details},
    ))

    return ItemResponse(item_id=item.id)


async def list_items(
    org_id: int,
    limit: int,
    offset: int,
    current_user: User,
    membership: Membership,
    db: AsyncSession,
) -> PaginatedItemsResponse:
    base_q = select(Item).where(Item.org_id == org_id)
    count_q = select(func.count()).select_from(Item).where(Item.org_id == org_id)

    # Members see only their own items but admins can see everything
    if membership.role == RoleEnum.member:
        base_q = base_q.where(Item.created_by == current_user.id)
        count_q = count_q.where(Item.created_by == current_user.id)

    total = (await db.execute(count_q)).scalar_one()
    rows = (await db.execute(base_q.limit(limit).offset(offset))).scalars().all()

    db.add(AuditLog(
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditActionEnum.item_viewed,
        details={"role": membership.role.value, "limit": limit, "offset": offset},
    ))

    return PaginatedItemsResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[ItemDetailResponse.model_validate(r) for r in rows],
    )