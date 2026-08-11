"""
Seed realistic upcoming events for each club.
Run: python -m scripts.seed_events
"""

import asyncio
import uuid
from datetime import datetime, timedelta
import random
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Club, Event, User

EVENTS_BY_CLUB = {
    "ai-club": [
        {"title": "GenAI Workshop: Building with LLMs", "description": "Hands-on workshop on LangChain, prompt engineering, and deploying LLM-powered apps. Build a mini AI assistant in 3 hours.", "location": "Lab 204, Block B", "capacity": 60, "days_from_now": 5},
        {"title": "AI Paper Reading Club — August Edition", "description": "Group discussion on recent papers from NeurIPS and ICML. This month: diffusion models and multimodal learning.", "location": "Seminar Hall 1", "capacity": 40, "days_from_now": 12},
        {"title": "ML Project Showcase", "description": "Students present their semester ML projects. Open to all branches. Prizes for top 3 projects.", "location": "Main Auditorium", "capacity": 200, "days_from_now": 21},
    ],
    "codex": [
        {"title": "CodeSprint 4.0 — 24hr Hackathon", "description": "Annual 24-hour competitive programming hackathon. Teams of 2-4. Prizes worth ₹50,000.", "location": "Computer Lab Complex", "capacity": 120, "days_from_now": 8},
        {"title": "CP Bootcamp: Dynamic Programming", "description": "Intensive 3-hour session on DP techniques for competitive programming. Codeforces problems solved live.", "location": "Lab 101, Block A", "capacity": 50, "days_from_now": 3},
    ],
    "gdsc": [
        {"title": "Google Cloud Study Jam", "description": "Free hands-on Google Cloud training with official Google Cloud certifications. Qwiklabs credits provided.", "location": "Lab 203", "capacity": 80, "days_from_now": 6},
        {"title": "Flutter Forward: Mobile Dev Workshop", "description": "Build a fully functional cross-platform app from scratch using Flutter and Firebase in one day.", "location": "Lab 101", "capacity": 45, "days_from_now": 14},
        {"title": "Solution Challenge Kickoff 2025", "description": "Kickoff session for Google Solution Challenge — build solutions for UN Sustainable Development Goals.", "location": "Seminar Hall 2", "capacity": 100, "days_from_now": 19},
    ],
    "cbc": [
        {"title": "Cyber Laws Seminar", "description": "Expert talk on cybercrime laws, data protection regulations, and legal frameworks for digital citizens.", "location": "Auditorium A", "capacity": 150, "days_from_now": 4},
        {"title": "Web3 Hackathon: DeFi Edition", "description": "Build decentralized finance applications on Ethereum. Smart contract development using Solidity.", "location": "Lab Complex B", "capacity": 60, "days_from_now": 16},
        {"title": "Ethical Hacking CTF", "description": "Capture the Flag competition testing web security, cryptography, and reverse engineering skills.", "location": "Lab 305", "capacity": 80, "days_from_now": 25},
    ],
    "robotics": [
        {"title": "ROS2 Workshop: Building Autonomous Bots", "description": "Practical workshop on Robot Operating System 2. Program a TurtleBot to navigate autonomously.", "location": "Robotics Lab, Block C", "capacity": 30, "days_from_now": 7},
        {"title": "Robocon Team Trials 2025", "description": "Open trials for the college Robocon team. All branches welcome. Basic programming knowledge required.", "location": "Workshop Area", "capacity": 50, "days_from_now": 10},
    ],
    "wwr": [
        {"title": "SUPRA SAE Design Review", "description": "Internal design review for the SUPRA SAE 2025 car. Aerodynamics, powertrain, and chassis teams present.", "location": "Workshop Bay, Block D", "capacity": 40, "days_from_now": 9},
        {"title": "Go-Kart Racing Day", "description": "Annual go-kart race open to all students. Come watch the team's custom-built karts in action.", "location": "Campus Track", "capacity": 200, "days_from_now": 30},
    ],
    "epic": [
        {"title": "SymbiTech 2025 — Annual Tech Fest", "description": "SIT's flagship tech-entrepreneurship festival. Hackathons, startup pitches, industry talks, and cultural events across 2 days.", "location": "Main Campus", "capacity": 500, "days_from_now": 15},
        {"title": "Startup Pitch Night", "description": "Present your startup idea to a panel of investors and mentors. Pre-registration required.", "location": "Seminar Hall 1", "capacity": 80, "days_from_now": 22},
    ],
    "edc": [
        {"title": "PCB Design Workshop with KiCad", "description": "Design your first PCB using KiCad. From schematic to Gerber files. Boards sent for fabrication.", "location": "Electronics Lab, Block B", "capacity": 35, "days_from_now": 11},
        {"title": "IoT Prototyping Bootcamp", "description": "Build a smart home sensor system using ESP32, MQTT, and Node-RED over one weekend.", "location": "Maker Space", "capacity": 40, "days_from_now": 18},
    ],
    "ieee": [
        {"title": "IEEE Talk: Future of 6G Networks", "description": "Distinguished lecture by IEEE senior member on next-generation wireless communication standards.", "location": "Seminar Hall 2", "capacity": 120, "days_from_now": 13},
    ],
    "foss": [
        {"title": "Hacktoberfest Prep Session", "description": "Get ready for Hacktoberfest! Learn how to find good first issues, write PRs, and contribute to major open-source projects.", "location": "Lab 202", "capacity": 60, "days_from_now": 2},
    ],
    "arvr": [
        {"title": "Unity XR Development Workshop", "description": "Build your first AR app using Unity and AR Foundation. Deploy on Android and iOS.", "location": "Lab 104", "capacity": 30, "days_from_now": 17},
    ],
    "mesa": [
        {"title": "Industry Visit: Tata Motors Pune Plant", "description": "Exclusive industry visit to the Tata Motors manufacturing plant. Limited seats — first come first served.", "location": "Tata Motors, Pune", "capacity": 40, "days_from_now": 20},
    ],
    "cess": [
        {"title": "Concrete Mix Design Competition", "description": "Teams compete to design the optimal concrete mix ratio. Judged on strength, workability, and cost.", "location": "Civil Engineering Lab", "capacity": 50, "days_from_now": 23},
    ],
    "sqc": [
        {"title": "Intro to Quantum Computing with Qiskit", "description": "Beginner-friendly session on quantum gates, superposition, and entanglement using IBM Qiskit.", "location": "Lab 301", "capacity": 45, "days_from_now": 26},
    ],
    "acm": [
        {"title": "ACM ICPC Team Selection", "description": "Selection contest for the college ICPC team. Top performers represent SIT at regionals.", "location": "Computer Lab A", "capacity": 60, "days_from_now": 28},
    ],
    "varsity-care": [
        {"title": "Blood Donation Drive", "description": "Annual blood donation camp in collaboration with Sahyadri Hospital. All students and staff welcome.", "location": "Main Cafeteria", "capacity": 300, "days_from_now": 1},
    ],
    "mosaic": [
        {"title": "Monsoon Theatrics — Annual Drama Fest", "description": "Two-day drama festival with performances, improv competitions, and a one-act play contest.", "location": "Open Air Theatre", "capacity": 250, "days_from_now": 27},
    ],
    "soultosole": [
        {"title": "Dance Battle: Crew Wars 3.0", "description": "Inter-college dance battle. 4-8 member crews compete across hip-hop, contemporary, and folk categories.", "location": "Main Auditorium", "capacity": 300, "days_from_now": 24},
    ],
    "sms": [
        {"title": "Unplugged Sessions — Acoustic Night", "description": "Intimate acoustic performances by students. Bring your instrument or just your voice.", "location": "Amphi Theatre", "capacity": 100, "days_from_now": 29},
    ],
    "tedx-mun": [
        {"title": "SymbiMUN 2025", "description": "Annual Model United Nations conference with 8 committees, 200 delegates, and 3 days of debate.", "location": "SIT Conference Centre", "capacity": 200, "days_from_now": 35},
    ],
    "antariksh": [
        {"title": "Meteor Shower Observation Night", "description": "Guided stargazing session during the Perseids meteor shower. Telescopes provided.", "location": "College Terrace", "capacity": 80, "days_from_now": 32},
    ],
}


async def main():
    print("=" * 50)
    print("SymbiCircle Event Seed Script")
    print("=" * 50)

    async with AsyncSessionLocal() as db:
        # get a real user to be organizer
        user_result = await db.execute(select(User).limit(1))
        organizer   = user_result.scalar_one_or_none()

        count = 0
        for club_slug, events in EVENTS_BY_CLUB.items():
            club_result = await db.execute(
                select(Club).where(Club.slug == club_slug)
            )
            club = club_result.scalar_one_or_none()
            if not club:
                print(f"  Club not found: {club_slug} — skipping")
                continue

            for event_data in events:
                # check if already exists
                existing = await db.execute(
                    select(Event).where(
                        Event.title == event_data["title"],
                        Event.club_id == club.id
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                event_date = datetime.now() + timedelta(days=event_data["days_from_now"])

                event = Event(
                    id=str(uuid.uuid4()),
                    title=event_data["title"],
                    description=event_data["description"],
                    club_id=club.id,
                    organizer_id=organizer.id if organizer else None,
                    location=event_data["location"],
                    event_date=event_date,
                    capacity=event_data["capacity"],
                    is_published=True,
                )
                db.add(event)
                count += 1

        await db.commit()
        print(f"  {count} events seeded.")

    print("=" * 50)
    print("Event seed complete.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())