from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from app.database import get_db
from app.models import Skill, SkillAlias, UserSkill
from app.schemas import SkillOut
from app.routers.auth import get_current_user
from app.models import User
import uuid

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/search", response_model=list[SkillOut])
async def search_skills(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Type-ahead search. Searches both skill names and aliases.
    Returns matching skills ordered by name.
    Used by the register and profile pages for the chip picker.
    """
    q_lower = q.strip().lower()

    # search skill names directly
    name_matches = await db.execute(
        select(Skill)
        .where(func.lower(Skill.name).contains(q_lower))
        .order_by(Skill.name)
        .limit(limit)
    )
    skills_by_name = name_matches.scalars().all()

    # search aliases and resolve to canonical skills
    alias_matches = await db.execute(
        select(SkillAlias)
        .where(func.lower(SkillAlias.alias_text).contains(q_lower))
        .limit(limit)
    )
    aliases = alias_matches.scalars().all()

    # collect canonical skill ids from aliases
    alias_skill_ids = [a.canonical_skill_id for a in aliases]

    canonical_skills = []
    if alias_skill_ids:
        canonical_result = await db.execute(
            select(Skill)
            .where(Skill.id.in_(alias_skill_ids))
            .order_by(Skill.name)
        )
        canonical_skills = canonical_result.scalars().all()

    # merge, deduplicate, preserve order
    seen_ids = set()
    merged = []
    for skill in skills_by_name + canonical_skills:
        if skill.id not in seen_ids:
            seen_ids.add(skill.id)
            merged.append(skill)

    return merged[:limit]


@router.post("/", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
async def create_skill(
    name: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a brand new skill if it doesn't exist yet.
    Called when user types a skill not found in search results.
    Requires authentication.
    """
    name_clean = name.strip()

    # check if already exists (case-insensitive)
    existing = await db.execute(
        select(Skill).where(func.lower(Skill.name) == name_clean.lower())
    )
    skill = existing.scalar_one_or_none()
    if skill:
        return skill

    # check aliases too — maybe it's already an alias of something
    alias_check = await db.execute(
        select(SkillAlias).where(
            func.lower(SkillAlias.alias_text) == name_clean.lower()
        )
    )
    alias = alias_check.scalar_one_or_none()
    if alias:
        canonical = await db.get(Skill, alias.canonical_skill_id)
        if canonical:
            return canonical

    # create new skill
    new_skill = Skill(
        id=str(uuid.uuid4()),
        name=name_clean,
        created_by=current_user.id,
    )
    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)
    return new_skill


@router.get("/", response_model=list[SkillOut])
async def list_all_skills(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns paginated list of all skills.
    Used to seed the type-ahead on initial page load.
    """
    result = await db.execute(
        select(Skill).order_by(Skill.name).limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.post("/alias", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
async def add_alias(
    canonical_skill_id: str = Query(...),
    alias_text: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Map an alias to a canonical skill.
    e.g. alias_text='NLP' → canonical='Natural Language Processing'
    This is the alias resolution layer for the semantic engine.
    """
    # verify canonical skill exists
    skill = await db.get(Skill, canonical_skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canonical skill not found.",
        )

    # check alias doesn't already exist
    existing = await db.execute(
        select(SkillAlias).where(
            func.lower(SkillAlias.alias_text) == alias_text.strip().lower()
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This alias already exists.",
        )

    new_alias = SkillAlias(
        id=str(uuid.uuid4()),
        alias_text=alias_text.strip(),
        canonical_skill_id=canonical_skill_id,
    )
    db.add(new_alias)
    await db.commit()
    return skill