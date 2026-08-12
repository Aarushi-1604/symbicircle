from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Club, UserClub, Event, EventRegistration, User
from app.schemas import ClubOut, ClubDetailOut, EventOut
from app.routers.auth import get_current_user
import uuid

router = APIRouter(prefix="/api/clubs", tags=["clubs"])


@router.get("", response_model=list[ClubOut])
async def list_clubs(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Club).order_by(Club.category, Club.name)
    if category:
        query = query.where(Club.category == category)

    result = await db.execute(query)
    clubs  = result.scalars().all()

    if not clubs:
        return []

    club_ids = [c.id for c in clubs]

    count_result = await db.execute(
        select(UserClub.club_id, func.count())
        .where(UserClub.club_id.in_(club_ids))
        .group_by(UserClub.club_id)
    )
    member_counts = dict(count_result.all())

    return [
        ClubOut(
            id=club.id,
            name=club.name,
            slug=club.slug,
            description=club.description,
            category=club.category,
            member_count=member_counts.get(club.id, 0),
        )
        for club in clubs
    ]


@router.get("/{slug}", response_model=ClubDetailOut)
async def get_club(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Club).where(Club.slug == slug))
    club   = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found.")

    count_result = await db.execute(
        select(func.count()).select_from(UserClub)
        .where(UserClub.club_id == club.id)
    )
    member_count = count_result.scalar() or 0

    events_result = await db.execute(
        select(Event)
        .where(Event.club_id == club.id, Event.is_published == True)
        .order_by(Event.event_date)
    )
    events = events_result.scalars().all()

    if not events:
        return ClubDetailOut(
            id=club.id, name=club.name, slug=club.slug,
            description=club.description, category=club.category,
            member_count=member_count, events=[],
        )

    event_ids = [e.id for e in events]

    reg_count_result = await db.execute(
        select(EventRegistration.event_id, func.count())
        .where(EventRegistration.event_id.in_(event_ids))
        .group_by(EventRegistration.event_id)
    )
    reg_counts = dict(reg_count_result.all())

    my_regs_result = await db.execute(
        select(EventRegistration.event_id)
        .where(
            EventRegistration.event_id.in_(event_ids),
            EventRegistration.user_id == current_user.id,
        )
    )
    my_registered_ids = {row[0] for row in my_regs_result.all()}

    event_outs = [
        EventOut(
            id=e.id,
            title=e.title,
            description=e.description,
            location=e.location,
            event_date=e.event_date,
            capacity=e.capacity,
            registered_count=reg_counts.get(e.id, 0),
            is_published=e.is_published,
            club_id=club.id,
            club_name=club.name,
            club_slug=club.slug,
            is_registered=e.id in my_registered_ids,
        )
        for e in events
    ]

    return ClubDetailOut(
        id=club.id, name=club.name, slug=club.slug,
        description=club.description, category=club.category,
        member_count=member_count, events=event_outs,
    )


@router.post("/{slug}/join", status_code=200)
async def join_club(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Club).where(Club.slug == slug))
    club   = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found.")

    existing = await db.execute(
        select(UserClub).where(
            UserClub.user_id == current_user.id,
            UserClub.club_id == club.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already a member.")

    db.add(UserClub(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        club_id=club.id,
        role="member",
    ))
    await db.commit()
    return {"detail": f"Joined {club.name}."}


@router.delete("/{slug}/join", status_code=200)
async def leave_club(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Club).where(Club.slug == slug))
    club   = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found.")

    existing = await db.execute(
        select(UserClub).where(
            UserClub.user_id == current_user.id,
            UserClub.club_id == club.id,
        )
    )
    uc = existing.scalar_one_or_none()
    if not uc:
        raise HTTPException(status_code=404, detail="Not a member.")

    await db.delete(uc)
    await db.commit()
    return {"detail": f"Left {club.name}."}