from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import User, UserSkill, Skill, SkillAlias
from app.routers.auth import get_current_user
from typing import List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

router = APIRouter(prefix="/search", tags=["search"])

# Branch-aware related skill clusters
# When a niche skill is searched, we expand using its cluster
SKILL_CLUSTERS = {
    # Robotics / RA cluster
    "slam":             ["robotics", "ros", "motion planning", "path planning", "sensor fusion", "computer vision", "embedded systems", "arduino", "raspberry pi"],
    "ros":              ["robotics", "slam", "motion planning", "path planning", "sensor fusion", "python", "c++"],
    "path planning":    ["robotics", "ros", "slam", "motion planning", "sensor fusion"],
    "motion planning":  ["robotics", "ros", "slam", "path planning"],
    "sensor fusion":    ["robotics", "ros", "slam", "computer vision", "embedded systems"],

    # ENTC cluster
    "fpga":             ["vlsi", "embedded systems", "c", "signal processing", "arm architecture", "microcontrollers"],
    "vlsi":             ["fpga", "embedded systems", "signal processing", "pcb design"],
    "pcb design":       ["vlsi", "embedded systems", "altium designer", "proteus", "circuit design"],
    "arm architecture": ["embedded systems", "microcontrollers", "fpga", "c", "c++"],

    # CIVIL cluster
    "staad pro":        ["structural analysis", "etabs", "autocad", "revit", "concrete design", "steel design"],
    "etabs":            ["structural analysis", "staad pro", "autocad", "revit", "earthquake engineering"],
    "revit":            ["autocad", "bim", "staad pro", "etabs", "construction management"],

    # MECH cluster
    "ansys":            ["fea analysis", "solidworks", "catia", "matlab", "thermodynamics", "fluid mechanics"],
    "catia":            ["solidworks", "ansys", "autocad", "cam", "cnc programming"],
    "cnc programming":  ["cam", "catia", "solidworks", "manufacturing processes", "machine design"],
    "fea analysis":     ["ansys", "solidworks", "matlab", "thermodynamics", "machine design"],

    # AIML cluster
    "langchain":        ["generative ai", "python", "natural language processing", "machine learning", "llm"],
    "hugging face":     ["natural language processing", "python", "deep learning", "transformers", "pytorch"],
    "reinforcement learning": ["machine learning", "deep learning", "python", "pytorch", "tensorflow"],

    # CSE cluster
    "graphql":          ["rest apis", "node.js", "react", "javascript", "typescript", "system design"],
    "kubernetes":       ["docker", "devops", "ci/cd", "cloud computing", "aws", "linux"],
    "redis":            ["postgresql", "mongodb", "sql", "system design", "node.js", "docker"],
}


async def resolve_skill_names(queries: List[str], db: AsyncSession) -> List[str]:
    resolved = set()
    for q in queries:
        q_lower = q.strip().lower()
        resolved.add(q_lower)

        # check alias → canonical
        alias_result = await db.execute(
            select(SkillAlias).where(func.lower(SkillAlias.alias_text) == q_lower)
        )
        alias = alias_result.scalar_one_or_none()
        if alias:
            canonical = await db.get(Skill, alias.canonical_skill_id)
            if canonical:
                resolved.add(canonical.name.lower())
                all_aliases = await db.execute(
                    select(SkillAlias).where(
                        SkillAlias.canonical_skill_id == canonical.id
                    )
                )
                for a in all_aliases.scalars().all():
                    resolved.add(a.alias_text.lower())

        # check canonical → all its aliases
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


def expand_with_clusters(resolved_terms: List[str]) -> List[str]:
    """
    Expand search terms using skill clusters.
    This gives TF-IDF enough vocabulary to find semantically
    related users even when no alias exists.
    """
    expanded = set(resolved_terms)
    for term in resolved_terms:
        if term in SKILL_CLUSTERS:
            expanded.update(SKILL_CLUSTERS[term])
    return list(expanded)


def build_user_skill_corpus(users: List[User]) -> List[str]:
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

    # 1. expand through alias graph
    expanded_terms = await resolve_skill_names(skills, db)

    # 2. further expand through skill clusters for TF-IDF
    cluster_expanded = expand_with_clusters(expanded_terms)

    # 3. load all active users with skills
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

    # 4. split into exact vs non-exact
    exact_users = []
    non_exact_users = []

    for user in all_users:
        user_skill_names = {us.skill.name.lower() for us in user.user_skills}
        user.skills = [us.skill for us in user.user_skills]

        matched = any(
            any(
                term in skill_name or skill_name in term
                for skill_name in user_skill_names
            )
            for term in expanded_terms
        )
        if matched:
            exact_users.append(user)
        else:
            non_exact_users.append(user)

    # 5. TF-IDF on non-exact users using cluster-expanded query
    similar_users = []

    if non_exact_users:
        try:
            # use cluster-expanded terms as the query document
            # this gives TF-IDF vocabulary overlap with related skills
            query_doc = " ".join(cluster_expanded)
            corpus    = build_user_skill_corpus(non_exact_users)
            all_docs  = [query_doc] + corpus

            vectorizer = TfidfVectorizer(
                analyzer='word',
                ngram_range=(1, 2),
                min_df=1,
                sublinear_tf=True,
            )
            tfidf_matrix  = vectorizer.fit_transform(all_docs)
            query_vec     = tfidf_matrix[0]
            user_vecs     = tfidf_matrix[1:]

            similarities  = cosine_similarity(query_vec, user_vecs).flatten()

            threshold = 0.01
            ranked = sorted(
                [
                    (non_exact_users[i], float(similarities[i]))
                    for i in range(len(non_exact_users))
                    if similarities[i] > threshold
                ],
                key=lambda x: x[1],
                reverse=True,
            )
            similar_users = [u for u, _ in ranked[:15]]

        except Exception:
            similar_users = []

    def serialize(user: User) -> dict:
        return {
            "id":         user.id,
            "username":   user.username,
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