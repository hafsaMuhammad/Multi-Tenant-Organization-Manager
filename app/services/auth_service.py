from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User, AuditLog, AuditActionEnum
from app.schemas.schemas import UserRegisterRequest, UserLoginRequest, TokenResponse


async def register_user(payload: UserRegisterRequest, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()  

    db.add(AuditLog(
        actor_id=user.id,
        action=AuditActionEnum.user_registered,
        details={"email": user.email},
    ))

    return user


async def login_user(payload: UserLoginRequest, db: AsyncSession) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.email == payload.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)