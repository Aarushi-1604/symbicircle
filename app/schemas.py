from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional
from datetime import datetime


ALLOWED_DOMAIN = "sitpune.edu.in"

VALID_BRANCHES = {"AIML", "CSE", "ENTC", "RA", "CIVIL", "MECH"}
VALID_BATCHES  = {"2023-27", "2024-28", "2025-29", "2026-30"}


# ── Skill ────────────────────────────────────────────────────────────────────

class SkillOut(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    branch: str
    batch: str
    skill_ids: List[str]

    @field_validator("email")
    @classmethod
    def must_be_campus_email(cls, v: str) -> str:
        if not v.lower().endswith(f"@{ALLOWED_DOMAIN}"):
            raise ValueError(f"Only @{ALLOWED_DOMAIN} email addresses are allowed.")
        return v.lower()

    @field_validator("branch")
    @classmethod
    def must_be_valid_branch(cls, v: str) -> str:
        if v.upper() not in VALID_BRANCHES:
            raise ValueError(f"Branch must be one of {sorted(VALID_BRANCHES)}")
        return v.upper()

    @field_validator("batch")
    @classmethod
    def must_be_valid_batch(cls, v: str) -> str:
        if v not in VALID_BATCHES:
            raise ValueError(f"Batch must be one of {sorted(VALID_BATCHES)}")
        return v

    @field_validator("skill_ids")
    @classmethod
    def minimum_five_skills(cls, v: List[str]) -> List[str]:
        if len(v) < 5:
            raise ValueError("A minimum of 5 skills is required to register.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    branch: str
    batch: str
    is_active: bool
    created_at: datetime
    skills: List[SkillOut] = []

    model_config = {"from_attributes": True}