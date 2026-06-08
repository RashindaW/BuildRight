from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai import service
from app.ai.context import ToolContext
from app.ai.history import build_prior_messages
from app.ai.menu_adapter import get_menu_for_assistant
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_optional_user
from app.core.errors import AppError, NotFoundError
from app.core.rate_limit import limiter
from app.core.security import verify_csrf
from app.models.chat import Conversation, Message
from app.safety.injection import looks_like_injection
from app.safety.moderation import screen_message
from app.schemas.chat import ChatMessageIn, ConversationOut
from app.services import audit_service

router = APIRouter(prefix="/chat", tags=["chat"])


def _resolve_conversation(db, conversation_id, user, session_id) -> Conversation:
    if conversation_id:
        conv = db.get(Conversation, conversation_id)
        if not conv:
            raise NotFoundError("Conversation")
        if conv.user_id and (not user or conv.user_id != user.id):
            raise NotFoundError("Conversation")
        if not conv.user_id and conv.session_id != session_id:
            raise NotFoundError("Conversation")
        return conv
    conv = Conversation(user_id=user.id if user else None,
                        session_id=None if user else session_id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _load_preferences(db: Session, user_id: str | None) -> dict[str, str]:
    if not user_id:
        return {}
    from app.models.user_memory import UserPreference
    rows = db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    ).scalars().all()
    return {r.key: r.value for r in rows}


@router.post("/stream", dependencies=[Depends(verify_csrf)])
@limiter.limit(settings.chat_rate_limit)
def chat_stream(
    request: Request,
    body: ChatMessageIn,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
    x_session_id: str | None = Header(default=None),
):
    allowed, reason = screen_message(body.message)
    if not allowed:
        raise AppError("Message rejected by content policy", reason, 400)

    session_id = x_session_id or str(uuid.uuid4())
    conv = _resolve_conversation(db, body.conversation_id, user, session_id)

    if conv.total_output_tokens >= settings.max_tokens_per_conversation:
        raise AppError("Conversation token budget reached. Please start a new chat.",
                       "budget_exceeded", 429)

    flagged = looks_like_injection(body.message)
    if flagged:
        audit_service.log(db, "chat.injection_flagged",
                          actor_id=user.id if user else None,
                          target=conv.id, note=body.message[:200])

    db.add(Message(conversation_id=conv.id, role="user", content=body.message))
    db.commit()

    full_menu = get_menu_for_assistant(db)
    preferences = _load_preferences(db, user.id if user else None)

    ctx = ToolContext(
        menu=full_menu,
        db=db,
        user_id=user.id if user else None,
        session_id=session_id,
        preferences=preferences,
    )

    history = build_prior_messages(
        db.execute(
            select(Message).where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        ).scalars().all()[:-1]
    )

    conv_id = conv.id

    async def event_gen():
        yield _sse("meta", {"conversation_id": conv_id, "session_id": session_id})
        assistant_text = ""
        out_tokens = 0
        grounded_ids: list[str] = []
        grounded_doc_ids: list[str] = []
        async for ev in service.stream_chat(history, ctx, body.message,
                                            max_tokens=settings.llm_max_tokens):
            if ev["event"] == "done":
                assistant_text = ev["data"]["text"]
                out_tokens = ev["data"].get("output_tokens", 0)
                grounded_ids = ev["data"].get("grounded_item_ids", [])
                grounded_doc_ids = ev["data"].get("grounded_doc_ids", [])
            yield _sse(ev["event"], ev["data"])
        from app.core.db import SessionLocal
        s = SessionLocal()
        try:
            s.add(Message(
                conversation_id=conv_id,
                role="assistant",
                content=assistant_text,
                grounded_item_ids=grounded_ids,
                grounded_doc_ids=grounded_doc_ids,
            ))
            c = s.get(Conversation, conv_id)
            if c:
                c.total_output_tokens += out_tokens
            s.commit()
        finally:
            s.close()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user=Depends(get_optional_user), db: Session = Depends(get_db),
                       x_session_id: str | None = Header(default=None)):
    stmt = select(Conversation).options(selectinload(Conversation.messages))
    if user:
        stmt = stmt.where(Conversation.user_id == user.id)
    elif x_session_id:
        stmt = stmt.where(Conversation.session_id == x_session_id)
    else:
        return []
    convs = db.execute(stmt.order_by(Conversation.created_at.desc())).scalars().all()
    return [ConversationOut.model_validate(c, from_attributes=True) for c in convs]


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: str, user=Depends(get_optional_user),
                     db: Session = Depends(get_db),
                     x_session_id: str | None = Header(default=None)):
    conv = _resolve_conversation(db, conversation_id, user, x_session_id)
    db.refresh(conv)
    return ConversationOut.model_validate(conv, from_attributes=True)
