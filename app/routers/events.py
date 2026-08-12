from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Event, EventRegistration, Club, User
from app.schemas import EventOut
from app.routers.auth import get_current_user
from typing import Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/events", tags=["events"])


async def serialize_event(
    event: Event,
    club: Club,
    db: AsyncSession,
    current_user_id: str,
) -> EventOut:
    reg_count = await db.execute(
        select(func.count()).select_from(EventRegistration)
        .where(EventRegistration.event_id == event.id)
    )
    is_registered = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event.id,
            EventRegistration.user_id == current_user_id,
        )
    )
    return EventOut(
        id=event.id,
        title=event.title,
        description=event.description,
        location=event.location,
        event_date=event.event_date,
        capacity=event.capacity,
        registered_count=reg_count.scalar() or 0,
        is_published=event.is_published,
        club_id=club.id,
        club_name=club.name,
        club_slug=club.slug,
        is_registered=is_registered.scalar_one_or_none() is not None,
    )


@router.get("", response_model=list[EventOut])
async def list_events(
    club_slug: Optional[str] = Query(None),
    upcoming_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Event, Club)
        .join(Club, Event.club_id == Club.id)
        .where(Event.is_published == True)
        .order_by(Event.event_date)
    )
    if club_slug:
        query = query.where(Club.slug == club_slug)
    if upcoming_only:
        query = query.where(Event.event_date >= datetime.now())

    result = await db.execute(query)
    rows   = result.all()

    if not rows:
        return []

    event_ids = [event.id for event, club in rows]

    # batch: registration count per event, one query total
    count_result = await db.execute(
        select(EventRegistration.event_id, func.count())
        .where(EventRegistration.event_id.in_(event_ids))
        .group_by(EventRegistration.event_id)
    )
    reg_counts = dict(count_result.all())

    # batch: which events the current user is registered for, one query total
    my_regs_result = await db.execute(
        select(EventRegistration.event_id)
        .where(
            EventRegistration.event_id.in_(event_ids),
            EventRegistration.user_id == current_user.id,
        )
    )
    my_registered_ids = {row[0] for row in my_regs_result.all()}

    out = []
    for event, club in rows:
        out.append(EventOut(
            id=event.id,
            title=event.title,
            description=event.description,
            location=event.location,
            event_date=event.event_date,
            capacity=event.capacity,
            registered_count=reg_counts.get(event.id, 0),
            is_published=event.is_published,
            club_id=club.id,
            club_name=club.name,
            club_slug=club.slug,
            is_registered=event.id in my_registered_ids,
        ))
    return out


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Event, Club)
        .join(Club, Event.club_id == Club.id)
        .where(Event.id == event_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found.")

    event, club = row
    return await serialize_event(event, club, db, current_user.id)


@router.get("/{event_id}/registered")
async def check_registration(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == current_user.id,
        )
    )
    return {"registered": result.scalar_one_or_none() is not None}


@router.post("/{event_id}/register", status_code=201)
async def register_for_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event  = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    if event.capacity:
        reg_count = await db.execute(
            select(func.count()).select_from(EventRegistration)
            .where(EventRegistration.event_id == event_id)
        )
        if (reg_count.scalar() or 0) >= event.capacity:
            raise HTTPException(status_code=409, detail="Event is at full capacity.")

    existing = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already registered.")

    db.add(EventRegistration(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        event_id=event_id,
    ))
    await db.commit()
    return {"detail": "Registered successfully."}


@router.delete("/{event_id}/register", status_code=200)
async def cancel_registration(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == current_user.id,
        )
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Not registered for this event.")

    await db.delete(reg)
    await db.commit()
    return {"detail": "Registration cancelled."}