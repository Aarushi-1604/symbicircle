"""
Seed all 24 SIT Pune clubs and randomly assign
students to 1-4 clubs each based on their branch.
Run: python -m scripts.seed_clubs
"""

import asyncio
import random
import uuid
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User, Club, UserClub

CLUBS = [
    # Technical
    {"name": "CodeX",                                    "slug": "codex",         "category": "technical",    "description": "Competitive programming and coding challenges club."},
    {"name": "IEEE",                                     "slug": "ieee",          "category": "technical",    "description": "IEEE student chapter for electronics and electrical engineering."},
    {"name": "GDSC",                                     "slug": "gdsc",          "category": "technical",    "description": "Google Developer Student Club — build for local businesses and communities."},
    {"name": "FOSS Club",                                "slug": "foss",          "category": "technical",    "description": "Free and Open Source Software club promoting open-source contributions."},
    {"name": "Symbiosis Quantum Club",                   "slug": "sqc",           "category": "technical",    "description": "Exploring quantum computing, cryptography, and emerging tech."},
    {"name": "AI Club",                                  "slug": "ai-club",       "category": "technical",    "description": "Artificial intelligence research, projects, and workshops."},
    {"name": "ARVR Game Dev Club",                       "slug": "arvr",          "category": "technical",    "description": "Augmented and virtual reality game development community."},
    {"name": "Electronic Design Club",                   "slug": "edc",           "category": "technical",    "description": "Circuit design, PCB fabrication, and embedded systems projects."},
    {"name": "Robotics and Automation",                  "slug": "robotics",      "category": "technical",    "description": "Robotics competitions, automation projects, and ROS workshops."},
    {"name": "ACM Student Chapter",                      "slug": "acm",           "category": "technical",    "description": "Association for Computing Machinery — algorithms, research, and tech talks."},
    {"name": "CyberBlockchain Club",                     "slug": "cbc",           "category": "technical",    "description": "Cybersecurity, blockchain development, and Web3 exploration."},
    {"name": "Mathletes",                                "slug": "mathletes",     "category": "technical",    "description": "Mathematics competitions, problem solving, and applied math projects."},
    {"name": "Rotonity Club",                            "slug": "rotonity",      "category": "technical",    "description": "Rotary-inspired networking and community innovation club."},

    # Engineering
    {"name": "MESA Club",                                "slug": "mesa",          "category": "engineering",  "description": "Mechanical Engineering Student Association — projects, workshops, and industry visits."},
    {"name": "Wrench Wielders Racing",                   "slug": "wwr",           "category": "engineering",  "description": "Formula-style racing team building and competing with student-built cars."},
    {"name": "Civil Engineering Society of Symbiosis",   "slug": "cess",          "category": "engineering",  "description": "Civil engineering projects, site visits, and structural competitions."},

    # Business / Innovation
    {"name": "EPIC",                                     "slug": "epic",          "category": "innovation",   "description": "Entrepreneurship Promotion and Innovation Cell — startups, pitches, and mentorship."},
    {"name": "Symbiosis Economics Club",                 "slug": "sec",           "category": "innovation",   "description": "Economics discussions, case studies, and finance workshops."},
    {"name": "TEDxMUN Club",                             "slug": "tedx-mun",      "category": "innovation",   "description": "TEDx talks and Model United Nations debate and diplomacy."},
    {"name": "Antariksh",                                "slug": "antariksh",     "category": "innovation",   "description": "Space and astronomy club — stargazing, ISRO collaborations, and astrophysics."},

    # Social / Cultural
    {"name": "V@rSITy Care",                             "slug": "varsity-care",  "category": "social",       "description": "Social awareness and community outreach through volunteering."},
    {"name": "MOSAIC",                                   "slug": "mosaic",        "category": "cultural",     "description": "Drama and performing arts club — productions, improv, and theatre workshops."},
    {"name": "SoultoSole",                               "slug": "soultosole",    "category": "cultural",     "description": "Dance club covering all styles — classical, contemporary, hip-hop, and fusion."},
    {"name": "Brushes2Pixels",                           "slug": "brushes2pixels","category": "cultural",     "description": "Art and design club — traditional art, digital illustration, and UI/UX."},
    {"name": "Symbiosis Music Society",                  "slug": "sms",           "category": "cultural",     "description": "Music performances, jam sessions, instrument workshops, and college fests."},
]

# Branch-weighted club affinity
# Students in certain branches are more likely to join certain clubs
BRANCH_CLUB_WEIGHTS = {
    "AIML": {
        "ai-club": 5, "codex": 4, "gdsc": 4, "foss": 3, "sqc": 3,
        "acm": 3, "arvr": 2, "cbc": 2, "mathletes": 2,
        "epic": 2, "sec": 1,
    },
    "CSE": {
        "codex": 5, "gdsc": 5, "foss": 4, "acm": 4, "cbc": 3,
        "ai-club": 3, "arvr": 2, "edc": 1, "epic": 2,
    },
    "ENTC": {
        "ieee": 5, "edc": 5, "sqc": 3, "robotics": 3, "codex": 2,
        "acm": 2, "cbc": 2, "foss": 2,
    },
    "RA": {
        "robotics": 6, "mesa": 3, "wwr": 3, "edc": 3, "ieee": 2,
        "sqc": 2, "antariksh": 2,
    },
    "CIVIL": {
        "cess": 6, "mesa": 2, "antariksh": 2, "epic": 2,
        "sec": 2, "varsity-care": 2,
    },
    "MECH": {
        "mesa": 6, "wwr": 5, "cess": 2, "ieee": 2,
        "epic": 2, "rotonity": 2,
    },
}

# universal clubs any branch can join
UNIVERSAL_CLUBS = [
    "epic", "varsity-care", "mosaic", "soultosole",
    "brushes2pixels", "sms", "tedx-mun", "sec", "antariksh",
    "rotonity", "mathletes",
]


async def seed_clubs(db) -> dict:
    print("Seeding clubs...")
    club_map = {}
    for club_data in CLUBS:
        result = await db.execute(select(Club).where(Club.slug == club_data["slug"]))
        club = result.scalar_one_or_none()
        if not club:
            club = Club(
                id=str(uuid.uuid4()),
                name=club_data["name"],
                slug=club_data["slug"],
                description=club_data["description"],
                category=club_data["category"],
            )
            db.add(club)
        club_map[club_data["slug"]] = club

    await db.flush()
    print(f"  {len(club_map)} clubs ready.")
    return club_map


def pick_clubs_for_branch(branch: str, club_map: dict, n: int) -> list:
    weights = BRANCH_CLUB_WEIGHTS.get(branch, {})
    all_slugs = list(club_map.keys())

    weighted_slugs = []
    slug_weights   = []

    for slug in all_slugs:
        w = weights.get(slug, 0.5)
        weighted_slugs.append(slug)
        slug_weights.append(w)

    # normalize weights
    total = sum(slug_weights)
    slug_weights = [w / total for w in slug_weights]

    chosen = set()
    attempts = 0
    while len(chosen) < n and attempts < 100:
        pick = random.choices(weighted_slugs, weights=slug_weights, k=1)[0]
        chosen.add(pick)
        attempts += 1

    return [club_map[slug] for slug in chosen]


async def assign_clubs_to_users(db, club_map: dict):
    print("Assigning clubs to users...")
    result = await db.execute(select(User))
    users  = result.scalars().all()

    count = 0
    for user in users:
        # check if user already has clubs
        existing = await db.execute(
            select(UserClub).where(UserClub.user_id == user.id)
        )
        if existing.scalars().first():
            continue

        n_clubs = random.randint(1, 4)
        clubs   = pick_clubs_for_branch(user.branch, club_map, n_clubs)

        for club in clubs:
            role = random.choices(
                ["member", "core", "lead"],
                weights=[85, 12, 3],
                k=1
            )[0]
            db.add(UserClub(
                id=str(uuid.uuid4()),
                user_id=user.id,
                club_id=club.id,
                role=role,
            ))
            count += 1

        if count % 500 == 0 and count > 0:
            await db.commit()
            print(f"  {count} club memberships committed...")

    await db.commit()
    print(f"  Done. {count} club memberships assigned.")


async def main():
    print("=" * 50)
    print("SymbiCircle Club Seed Script")
    print("=" * 50)

    async with AsyncSessionLocal() as db:
        club_map = await seed_clubs(db)
        await db.commit()
        await assign_clubs_to_users(db, club_map)

    print("=" * 50)
    print("Club seed complete.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())