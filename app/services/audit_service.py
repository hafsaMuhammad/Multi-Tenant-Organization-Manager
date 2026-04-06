from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditLog
from app.schemas.schemas import AuditLogResponse


async def get_audit_logs(org_id: int, db: AsyncSession) -> list[AuditLogResponse]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.org_id == org_id)
        .order_by(AuditLog.created_at.desc())
    )
    logs = result.scalars().all()
    return [AuditLogResponse.model_validate(log) for log in logs]