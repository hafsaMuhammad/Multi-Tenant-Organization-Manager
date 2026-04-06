import json
from datetime import datetime, timezone
from typing import AsyncGenerator

import google.generativeai as genai

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import AuditLog


def _build_system_prompt():

    today = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    return (

        f"You are an AI assistant helping organization admins "
        f"understand activity logs.\n"

        f"Today's date is {today}.\n"

        "Answer ONLY from logs.\n"

        "If not enough info say so."

    )


def _get_model():

    genai.configure(

        api_key=settings.GEMINI_API_KEY

    )

    return genai.GenerativeModel(

        "gemini-2.0-flash"

    )


async def _get_todays_logs(

    org_id:int,
    db:AsyncSession

)->list[dict]:

    today_start = datetime.now(

        timezone.utc

    ).replace(

        hour=0,
        minute=0,
        second=0,
        microsecond=0

    )

    result = await db.execute(

        select(AuditLog)

        .where(

            AuditLog.org_id==org_id,

            AuditLog.created_at>=today_start

        )

        .order_by(

            AuditLog.created_at.asc()

        )

    )

    logs=result.scalars().all()

    return [

        {

            "id":log.id,
            "action":log.action.value,
            "actor_id":log.actor_id,
            "details":log.details,
            "created_at":log.created_at.isoformat(),

        }

        for log in logs

    ]


async def ask_chatbot(

    org_id:int,
    question:str,
    db:AsyncSession

)->str:

    logs = await _get_todays_logs(

        org_id,
        db

    )

    logs_json=json.dumps(

        logs,
        indent=2

    )

    model=_get_model()

    prompt=f"""

    {_build_system_prompt()}

    Audit logs:

    {logs_json}

    Question:

    {question}

    """

    response=model.generate_content(

        prompt

    )

    return response.text


async def ask_chatbot_stream(

    org_id:int,
    question:str,
    db:AsyncSession

)->AsyncGenerator[str,None]:

    logs = await _get_todays_logs(

        org_id,
        db

    )

    logs_json=json.dumps(

        logs,
        indent=2

    )

    model=_get_model()

    prompt=f"""

    {_build_system_prompt()}

    Audit logs:

    {logs_json}

    Question:

    {question}

    """

    response=model.generate_content(

        prompt,
        stream=True

    )

    for chunk in response:

        if chunk.text:

            yield f"data: {json.dumps({'chunk':chunk.text})}\n\n"

    yield "data: [DONE]\n\n"