from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.models import (
    AuditActionEnum, AuditLog, Membership, Organization, RoleEnum, User
)
from app.schemas.schemas import (
    CreateOrgRequest, InviteUserRequest, OrgResponse,
    PaginatedUsersResponse, UserWithRoleResponse,
)


async def create_organization(
    payload: CreateOrgRequest,
    current_user: User,
    db: AsyncSession,
) -> OrgResponse:
    # Create the org
    org = Organization(name=payload.org_name)
    db.add(org)
    await db.flush()  
    membership = Membership(
        user_id=current_user.id,
        org_id=org.id,
        role=RoleEnum.admin
    )
    db.add(membership)

    # Log it in audit log
    db.add(AuditLog(
        org_id=org.id,
        actor_id=current_user.id,
        action=AuditActionEnum.org_created,
        details={"org_name": org.name},
    ))

    return OrgResponse(org_id=org.id)


async def invite_user(
    org_id: int,
    payload: InviteUserRequest,
    actor: User,
    db: AsyncSession,
) -> dict:
    result = await db.execute(
        select(User).where(User.email == payload.email, User.is_active == True)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    
    existing = await db.execute(
        select(Membership).where(
            Membership.user_id == target.id,
            Membership.org_id == org_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already a member")

    db.add(Membership(user_id=target.id, org_id=org_id, role=payload.role))

    db.add(AuditLog(
        org_id=org_id,
        actor_id=actor.id,
        action=AuditActionEnum.user_invited,
        details={
            "invited_user_id": target.id,
            "invited_email": target.email,
            "role": payload.role.value,
        },
    ))

    return {"message": "User invited", "user_id": target.id, "role": payload.role}


async def list_org_users(
    org_id: int,
    limit: int,
    offset: int,
    db: AsyncSession,
) -> PaginatedUsersResponse:
    # Total count
    total = (await db.execute(
        select(func.count())
        .select_from(Membership)
        .where(Membership.org_id == org_id)
    )).scalar_one()

    rows = (await db.execute(
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.org_id == org_id)
        .limit(limit)
        .offset(offset)
    )).all()

    users = [
        UserWithRoleResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            created_at=u.created_at,
            role=role,
        )
        for u, role in rows
    ]

    return PaginatedUsersResponse(total=total, limit=limit, offset=offset, users=users)


async def search_org_users(
    org_id: int,
    q: str,
    db: AsyncSession,
) -> list[UserWithRoleResponse]:
    from sqlalchemy import text

    rows = (await db.execute(
        text("""
            SELECT u.id, u.email, u.full_name, u.is_active, u.created_at, m.role
            FROM users u
            JOIN memberships m ON m.user_id = u.id
            WHERE m.org_id = :org_id
              AND to_tsvector('english', u.full_name || ' ' || u.email)
                  @@ plainto_tsquery('english', :query)
            LIMIT 50
        """),
        {"org_id": org_id, "query": q}
    )).mappings().all()

    return [
        UserWithRoleResponse(
            id=r["id"],
            email=r["email"],
            full_name=r["full_name"],
            is_active=r["is_active"],
            created_at=r["created_at"],
            role=r["role"],
        )
        for r in rows
    ]