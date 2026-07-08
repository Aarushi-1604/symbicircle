from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import User, UserSkill, Skill, SkillAlias
from app.schemas import UserOut
from app.routers.auth import get_current_user
from typing import List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

router = APIRouter(prefix="/search", tags=["search"])


async def resolve_skill_names(queries: List[str], db: AsyncSession) -> List[str]:
    """
    Expand each query term into itself + all its aliases + canonical names.
    e.g. 'NLP' → ['NLP', 'Natural Language Processing', 'Text Mining']
    """
    resolved = set()
    for q in queries:
        q_lower = q.strip().lower()
        resolved.add(q_lower)

        # check if query is an alias → get canonical name
        alias_result = await db.execute(
            select(SkillAlias).where(func.lower(SkillAlias.alias_text) == q_lower)
        )
        alias = alias_result.scalar_one_or_none()
        if alias:
            canonical = await db.get(Skill, alias.canonical_skill_id)
            if canonical:
                resolved.add(canonical.name.lower())
                # also grab all other aliases of this canonical skill
                all_aliases = await db.execute(
                    select(SkillAlias).where(
                        SkillAlias.canonical_skill_id == canonical.id
                    )
                )
                for a in all_aliases.scalars().all():
                    resolved.add(a.alias_text.lower())

        # check if query IS a canonical skill → grab all its aliases
        skill_result = await db.execute(
            select(Skill).where(func.lower(Skill.name) == q_lower)
        )
        skill = skill_result.scalar_one_or_none()
        if skill:
            all_aliases = await db.execute(
                select(SkillAlias).where(SkillAlias.canonical_skill_id == skill.id)
            )
            for a in all_aliases.scalars().all():
                resolved.add(a.alias_text.lower())

    return list(resolved)


def build_user_skill_corpus(users: List[User]) -> List[str]:
    """
    Each user becomes a document: their skills joined as a space-separated string.
    TF-IDF vectorizes this for cosine similarity matching.
    """
    return [
        " ".join(us.skill.name.lower() for us in u.user_skills)
        for u in users
    ]


@router.get("", response_model=dict)
async def search_users(
    skills: List[str] = Query(..., min_length=1),
    branch: Optional[str] = Query(None),
    batch: List[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not skills or all(s.strip() == "" for s in skills):
        raise HTTPException(status_code=400, detail="At least one skill query is required.")

    # 1. expand queries through alias graph
    expanded_terms = await resolve_skill_names(skills, db)

    # 2. load all active users with their skills
    query = (
        select(User)
        .options(selectinload(User.user_skills).selectinload(UserSkill.skill))
        .where(User.is_active == True, User.id != current_user.id)
    )
    if branch:
        query = query.where(func.upper(User.branch) == branch.upper())
    if batch:
        query = query.where(User.batch.in_(batch))

    result = await db.execute(query)
    all_users = result.scalars().all()

    if not all_users:
        return {"exact": [], "similar": []}

    # 3. exact match — user has at least one skill matching any expanded term
    exact_users = []
    non_exact_users = []

    for user in all_users:
        user_skill_names = {us.skill.name.lower() for us in user.user_skills}
        user.skills = [us.skill for us in user.user_skills]

        # check if any expanded term matches any of the user's skills
        matched = any(
            any(term in skill_name or skill_name in term
                for skill_name in user_skill_names)
            for term in expanded_terms
        )
        if matched:
            exact_users.append(user)
        else:
            non_exact_users.append(user)

    # 4. TF-IDF cosine similarity for "similar" fallback
    similar_users = []

    if non_exact_users:
        try:
            query_doc   = " ".join(expanded_terms)
            corpus      = build_user_skill_corpus(non_exact_users)
            all_docs    = [query_doc] + corpus

            vectorizer  = TfidfVectorizer(
                analyzer='word',
                ngram_range=(1, 2),
                min_df=1,
                sublinear_tf=True,
            )
            tfidf_matrix = vectorizer.fit_transform(all_docs)
            query_vec    = tfidf_matrix[0]
            user_vecs    = tfidf_matrix[1:]

            similarities = cosine_similarity(query_vec, user_vecs).flatten()

            # take users above similarity threshold, ranked
            threshold    = 0.05
            ranked       = sorted(
                [(non_exact_users[i], float(similarities[i]))
                 for i in range(len(non_exact_users))
                 if similarities[i] > threshold],
                key=lambda x: x[1],
                reverse=True,
            )
            similar_users = [u for u, _ in ranked[:12]]

        except Exception:
            similar_users = []

    # 5. serialize — reuse UserOut structure
    def serialize(user: User) -> dict:
        return {
            "id":         user.id,
            "full_name":  user.full_name,
            "email":      user.email,
            "branch":     user.branch,
            "batch":      user.batch,
            "is_active":  user.is_active,
            "created_at": user.created_at.isoformat(),
            "skills":     [{"id": s.id, "name": s.name} for s in (user.skills or [])],
        }

    return {
        "exact":   [serialize(u) for u in exact_users],
        "similar": [serialize(u) for u in similar_users],
    }