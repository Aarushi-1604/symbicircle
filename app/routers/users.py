from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import User, UserSkill, Skill
from app.schemas import UserOut, SkillOut
from app.routers.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])


class AddSkillRequest(BaseModel):
    skill_id: str


@router.get("/me", response_model=UserOut)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_skills).selectinload(UserSkill.skill))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one()
    user.skills = [us.skill for us in user.user_skills]
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_skills).selectinload(UserSkill.skill))
        .where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.skills = [us.skill for us in user.user_skills]
    return user


@router.post("/me/skills", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
async def add_skill_to_profile(
    payload: AddSkillRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = await db.get(Skill, payload.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found.")

    existing = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == current_user.id,
            UserSkill.skill_id == payload.skill_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Skill already on your profile.")

    db.add(UserSkill(user_id=current_user.id, skill_id=payload.skill_id))
    await db.commit()
    return skill


@router.delete("/me/skills/{skill_id}", status_code=status.HTTP_200_OK)
async def remove_skill_from_profile(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == current_user.id,
            UserSkill.skill_id == skill_id,
        )
    )
    user_skill = result.scalar_one_or_none()
    if not user_skill:
        raise HTTPException(status_code=404, detail="Skill not on your profile.")

    await db.delete(user_skill)
    await db.commit()
    return {"detail": "Skill removed."}