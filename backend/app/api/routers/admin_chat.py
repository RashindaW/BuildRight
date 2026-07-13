"""Admin 'ask your data' chat — manager-gated, SSE, reusing service.stream_chat with the
analytics toolset + admin persona (price guardrail off; answers quote real figures)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import service
from app.ai.admin_tools import ADMIN_EXECUTORS, ADMIN_SYSTEM_PROMPT, ADMIN_TOOLS
from app.ai.context import ToolContext
from app.ai.history import build_prior_messages
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import require_manager
from app.core.errors import AppError, NotFoundError
from app.core.rate_limit import limiter
from app.core.security import verify_csrf
from app.models.chat import Conversation, Message
from app.safety.moderation import screen_message
from app.schemas.chat import ChatMessageIn

router = APIRouter(prefix="/admin/chat", tags=["admin-chat"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream", dependencies=[Depends(verify_csrf)])
@limiter.limit(settings.chat_rate_limit)
def admin_chat_stream(
    request: Request,
    body: ChatMessageIn,
    db: Session = Depends(get_db),
    user=Depends(require_manager),
):
    allowed, reason = screen_message(body.message)
    if not allowed:
        raise AppError("Message rejected by content policy", reason, 400)

    if body.conversation_id:
        conv = db.get(Conversation, body.conversation_id)
        if not conv or conv.user_id != user.id:
            raise NotFoundError("Conversation")
    else:
        conv = Conversation(user_id=user.id, session_id=None)
        db.add(conv)
        db.commit()
        db.refresh(conv)

    db.add(Message(conversation_id=conv.id, role="user", content=body.message))
    db.commit()

    ctx = ToolContext(
        menu=[], db=db, user_id=user.id, session_id=None, conversation_id=conv.id, preferences={}
    )
    history = build_prior_messages(
        db.execute(
            select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
        ).scalars().all()[:-1]
    )
    conv_id = conv.id

    async def event_gen():
        yield _sse("meta", {"conversation_id": conv_id})
        assistant_text = ""
        meta: dict = {}
        async for ev in service.stream_chat(
            history,
            ctx,
            body.message,
            max_tokens=settings.llm_max_tokens,
            system_prompt=ADMIN_SYSTEM_PROMPT,
            tools_override=ADMIN_TOOLS,
            executors_override=ADMIN_EXECUTORS,
            validate_prices=False,
        ):
            if ev["event"] == "done":
                assistant_text = ev["data"]["text"]
                meta = ev["data"]
            yield _sse(ev["event"], ev["data"])

        from app.core.db import SessionLocal

        s = SessionLocal()
        try:
            in_t = int(meta.get("input_tokens", 0) or 0)
            out_t = int(meta.get("output_tokens", 0) or 0)
            s.add(Message(
                conversation_id=conv_id, role="assistant", content=assistant_text,
                model=meta.get("model"), route=meta.get("route"),
                input_tokens=in_t, output_tokens=out_t,
                tools_used=meta.get("tools_used") or [],
                guardrail_violation=bool(meta.get("guardrail_violation", False)),
                predicted_difficulty=meta.get("predicted_difficulty"),
                escalated=bool(meta.get("escalated", False)),
                router_version=meta.get("router_version"),
                cost_usd=meta.get("cost_usd"),
            ))
            c = s.get(Conversation, conv_id)
            if c:
                c.total_input_tokens += in_t
                c.total_output_tokens += out_t
            s.commit()
        finally:
            s.close()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
