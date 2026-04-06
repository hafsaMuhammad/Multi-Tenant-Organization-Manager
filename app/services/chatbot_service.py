import json
from datetime import datetime, timezone
from typing import AsyncGenerator

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import AuditLog


def _build_system_prompt() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"You are an AI assistant helping organization admins understand activity logs. "
        f"Today's date is {today}. "
        f"Answer the admin's question based solely on the audit logs provided. "
        f"Be concise and factual. If the logs don't contain enough information, say so."
    )


async def _get_todays_logs(org_id: int, db: AsyncSession) -> list[dict]:
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.org_id == org_id, AuditLog.created_at >= today_start)
        .order_by(AuditLog.created_at.asc())
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action": log.action.value,
            "actor_id": log.actor_id,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


async def ask_chatbot(org_id: int, question: str, db: AsyncSession) -> str:
    logs = await _get_todays_logs(org_id, db)
    logs_json = json.dumps(logs, indent=2)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=_build_system_prompt(),
        messages=[{
            "role": "user",
            "content": f"Today's audit logs:\n{logs_json}\n\nQuestion: {question}",
        }],
    )
    return message.content[0].text


async def ask_chatbot_stream(
    org_id: int,
    question: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    logs = await _get_todays_logs(org_id, db)
    logs_json = json.dumps(logs, indent=2)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=_build_system_prompt(),
        messages=[{
            "role": "user",
            "content": f"Today's audit logs:\n{logs_json}\n\nQuestion: {question}",
        }],
    ) as stream:
        for chunk in stream.text_stream:
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

    yield "data: [DONE]\n\n"