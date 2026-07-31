"""
SymbiCircle — Synthetic seed script
Generates 1000+ realistic SIT Pune students across all branches
with varied skill sets (technical + soft) and alias coverage.
Run: python -m scripts.seed
"""

import asyncio
import random
import uuid
from faker import Faker
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User, Skill, UserSkill, SkillAlias
from app.services.auth import hash_password
from app.services.slugify import generate_username

fake = Faker('en_IN')  # Indian locale for realistic names

# ── BRANCH SKILL POOLS ────────────────────────────────────────────────────────
# Each branch has a weighted skill pool — technical + soft skills mixed

SKILL_POOLS = {
    "AIML": {
        "technical": [
            "Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
            "Natural Language Processing", "Computer Vision", "Data Analysis",
            "Scikit-learn", "Keras", "OpenCV", "Hugging Face", "FastAPI",
            "Data Visualization", "SQL", "NumPy", "Pandas", "Matplotlib",
            "Reinforcement Learning", "Generative AI", "LangChain", "Docker",
            "Git", "Linux", "Jupyter Notebook", "Streamlit", "AWS",
        ],
        "soft": [
            "Research Writing", "Critical Thinking", "Problem Solving",
            "Presentation Skills", "Team Collaboration", "Technical Documentation",
            "Project Management", "Public Speaking",
        ]
    },
    "CSE": {
        "technical": [
            "Python", "JavaScript", "Java", "C++", "React", "Node.js",
            "FastAPI", "Django", "SQL", "MongoDB", "Docker", "Kubernetes",
            "Git", "Linux", "AWS", "Firebase", "TypeScript", "REST APIs",
            "GraphQL", "Redis", "PostgreSQL", "System Design", "Cybersecurity",
            "Blockchain", "Flutter", "Android Development", "iOS Development",
            "DevOps", "CI/CD", "Figma",
        ],
        "soft": [
            "Problem Solving", "Team Collaboration", "Agile Methodology",
            "Technical Documentation", "Code Review", "Mentoring",
            "Public Speaking", "Project Management",
        ]
    },
    "ENTC": {
        "technical": [
            "Embedded Systems", "Arduino", "Raspberry Pi", "MATLAB",
            "Signal Processing", "PCB Design", "VLSI", "IoT", "C", "C++",
            "Microcontrollers", "FPGA", "LabVIEW", "Proteus", "Altium Designer",
            "ARM Architecture", "Python", "Communication Systems",
            "Circuit Design", "Wireless Networks", "5G Technology",
            "Antenna Design", "Power Electronics",
        ],
        "soft": [
            "Technical Documentation", "Problem Solving", "Research Writing",
            "Team Collaboration", "Critical Thinking", "Presentation Skills",
        ]
    },
    "RA": {
        "technical": [
            "Robotics", "ROS", "Python", "C++", "MATLAB", "Computer Vision",
            "Machine Learning", "Embedded Systems", "Arduino", "Raspberry Pi",
            "SolidWorks", "AutoCAD", "3D Printing", "PLC Programming",
            "Motion Planning", "Sensor Fusion", "Control Systems",
            "Mechatronics", "Servo Systems", "Path Planning", "SLAM",
            "Hydraulics", "Pneumatics",
        ],
        "soft": [
            "Technical Documentation", "Problem Solving", "Team Collaboration",
            "Critical Thinking", "Research Writing", "Project Management",
        ]
    },
    "CIVIL": {
        "technical": [
            "AutoCAD", "STAAD Pro", "ETABS", "Revit", "Structural Analysis",
            "Concrete Design", "Steel Design", "Surveying", "GIS",
            "Construction Management", "Building Information Modeling",
            "Primavera", "MS Project", "Geotechnical Engineering",
            "Water Resources", "Environmental Engineering", "Highway Design",
            "Bridge Engineering", "Earthquake Engineering",
        ],
        "soft": [
            "Project Management", "Technical Documentation", "Team Collaboration",
            "Public Speaking", "Report Writing", "Critical Thinking",
            "Site Management", "Negotiation",
        ]
    },
    "MECH": {
        "technical": [
            "SolidWorks", "AutoCAD", "CATIA", "ANSYS", "MATLAB",
            "Thermodynamics", "Fluid Mechanics", "Manufacturing Processes",
            "CNC Programming", "3D Printing", "CAM", "FEA Analysis",
            "Heat Transfer", "Machine Design", "Metrology",
            "Hydraulics", "Pneumatics", "Welding", "Python",
            "Industrial Automation", "Six Sigma", "Lean Manufacturing",
        ],
        "soft": [
            "Technical Documentation", "Problem Solving", "Team Collaboration",
            "Project Management", "Critical Thinking", "Report Writing",
            "Presentation Skills", "Quality Control",
        ]
    }
}

# common soft skills that any branch can have
UNIVERSAL_SOFT_SKILLS = [
    "Communication", "Leadership", "Time Management", "Adaptability",
    "Creativity", "Emotional Intelligence", "Networking", "Canva",
    "Microsoft Office", "Google Workspace", "Content Writing",
    "Social Media Management", "Photography", "Video Editing",
    "Event Management", "Fundraising", "Volunteer Management",
]

BRANCHES = ["AIML", "CSE", "ENTC", "RA", "CIVIL", "MECH"]
BATCHES  = ["2023-27", "2024-28", "2025-29", "2026-30"]

# branch distribution — weighted toward AIML/CSE since that's realistic for SIT
BRANCH_WEIGHTS = [30, 28, 15, 10, 8, 9]


async def get_or_create_skill(db, name: str) -> Skill:
    result = await db.execute(
        select(Skill).where(Skill.name == name)
    )
    skill = result.scalar_one_or_none()
    if not skill:
        skill = Skill(
            id=str(uuid.uuid4()),
            name=name,
            created_by=None,
        )
        db.add(skill)
        await db.flush()
    return skill

async def seed_skills(db) -> dict:
    print("Seeding skill pool...")
    all_skill_names = set(UNIVERSAL_SOFT_SKILLS)
    for pool in SKILL_POOLS.values():
        all_skill_names.update(pool["technical"])
        all_skill_names.update(pool["soft"])

    skill_map = {}

    for name in sorted(all_skill_names):
        result = await db.execute(select(Skill).where(Skill.name == name))
        skill = result.scalar_one_or_none()
        if not skill:
            skill = Skill(
                id=str(uuid.uuid4()),
                name=name,
                created_by=None,
            )
            db.add(skill)
        skill_map[name] = skill

    await db.flush()
    print(f"  {len(skill_map)} skills ready.")
    return skill_map


async def seed_aliases(db, skill_map: dict):
    """Add alias mappings for the semantic engine."""
    print("Seeding aliases...")
    aliases = {
        "Natural Language Processing": ["NLP", "Text Mining", "Text Analytics"],
        "Machine Learning":            ["ML", "Statistical Learning"],
        "Deep Learning":               ["DL", "Neural Networks", "ANN"],
        "Data Analysis":               ["Data Analytics", "Data Analyst"],
        "JavaScript":                  ["JS"],
        "Python":                      ["Py"],
        "Computer Vision":             ["CV", "Image Processing"],
        "React":                       ["ReactJS", "React.js"],
        "Node.js":                     ["NodeJS", "Node"],
        "SolidWorks":                  ["Solid Works"],
        "AutoCAD":                     ["Auto CAD", "CAD"],
        "Thermodynamics":              ["Thermodynamic"],
        "Embedded Systems":            ["Embedded", "Embedded C"],
        "Cybersecurity":               ["Cyber Security", "InfoSec", "Information Security"],
        "Reinforcement Learning":      ["RL"],
        "Generative AI":               ["GenAI", "Gen AI"],
        "Flutter":                     ["Flutter Dev"],
        "Docker":                      ["Containerization"],
        "Git":                         ["GitHub", "Version Control"],
        "Communication":               ["Communication Skills"],
        "Public Speaking":             ["Oratory", "Debate"],
        "Content Writing":             ["Copywriting", "Technical Writing"],
        "Video Editing":               ["Video Production"],
        "3D Printing":                 ["Additive Manufacturing"],
    }

    count = 0
    for skill_name, alias_list in aliases.items():
        skill = skill_map.get(skill_name)
        if not skill:
            continue
        for alias_text in alias_list:
            result = await db.execute(
                select(SkillAlias).where(SkillAlias.alias_text == alias_text)
            )
            if not result.scalar_one_or_none():
                db.add(SkillAlias(
                    id=str(uuid.uuid4()),
                    alias_text=alias_text,
                    canonical_skill_id=skill.id,
                ))
                count += 1

    await db.flush()
    print(f"  {count} new aliases seeded.")


def pick_skills_for_branch(branch: str, n: int) -> list[str]:
    """
    Pick n skills for a user in a given branch.
    Mix: 60-75% technical, 25-40% soft (branch + universal).
    """
    pool      = SKILL_POOLS[branch]
    n_tech    = max(3, int(n * random.uniform(0.6, 0.75)))
    n_soft    = n - n_tech

    tech_picks = random.sample(pool["technical"],
                               min(n_tech, len(pool["technical"])))

    # soft skills: mix branch-specific and universal
    soft_combined = pool["soft"] + UNIVERSAL_SOFT_SKILLS
    soft_picks    = random.sample(soft_combined,
                                  min(n_soft, len(soft_combined)))

    combined = list(set(tech_picks + soft_picks))
    random.shuffle(combined)
    return combined[:n]


async def seed_users(db, skill_map: dict, count: int = 1000):
    """Generate count synthetic students."""
    print(f"Seeding {count} users...")

    hashed_pw = hash_password("SITpune@2024")  # shared demo password

    # check existing count
    existing = await db.execute(select(User))
    existing_count = len(existing.scalars().all())
    print(f"  {existing_count} users already exist, adding {count} more.")

    created = 0
    batch_size = 50  # flush every 50 users to avoid memory issues

    for i in range(count):
        branch = random.choices(BRANCHES, weights=BRANCH_WEIGHTS, k=1)[0]
        batch  = random.choice(BATCHES)

        # generate realistic Indian name
        full_name = fake.name()
        # clean name — remove titles like Dr., Mr., Mrs.
        for title in ["Dr. ", "Mr. ", "Mrs. ", "Ms. ", "Prof. "]:
            full_name = full_name.replace(title, "")
        full_name = full_name.strip()

        # generate SIT-style email
        name_parts  = full_name.lower().split()
        fname       = name_parts[0] if name_parts else "student"
        lname       = name_parts[-1] if len(name_parts) > 1 else "sit"
        year        = batch.split("-")[0][2:]  # '2024-28' → '24'
        email_local = f"{fname}.{lname}.btech{year}{random.randint(1000,9999)}"
        email       = f"{email_local}@sitpune.edu.in"

        # skip if email collision
        existing_email = await db.execute(select(User).where(User.email == email))
        if existing_email.scalar_one_or_none():
            continue

        user_id = str(uuid.uuid4())

        user = User(
            id=user_id,
            full_name=full_name,
            email=email,
            hashed_password=hashed_pw,
            branch=branch,
            batch=batch,
            is_active=True,
        )
        user.username = generate_username(full_name, user_id)
        db.add(user)
        await db.flush()

        # assign 5–15 skills
        n_skills   = random.randint(5, 15)
        skill_names = pick_skills_for_branch(branch, n_skills)

        seen = set()
        for name in skill_names:
            skill = skill_map.get(name)
            if not skill or skill.id in seen:
                continue
            seen.add(skill.id)
            db.add(UserSkill(
                id=str(uuid.uuid4()),
                user_id=user.id,
                skill_id=skill.id,
            ))

        created += 1

        # flush in batches
        if created % batch_size == 0:
            await db.commit()
            print(f"  {created}/{count} users committed...")

    await db.commit()
    print(f"  Done. {created} users created.")


async def main():
    print("=" * 50)
    print("SymbiCircle Seed Script")
    print("=" * 50)

    async with AsyncSessionLocal() as db:
        skill_map = await seed_skills(db)
        await db.commit()

        await seed_aliases(db, skill_map)
        await db.commit()

        await seed_users(db, skill_map, count=1000)

    print("=" * 50)
    print("Seed complete.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())