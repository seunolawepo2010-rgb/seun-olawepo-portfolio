import asyncio
import json
import os
import sys
from database import DatabaseManager
from datetime import datetime

# Mock data (copied from frontend for seeding)
portfolio_data = {
    "hero": {
        "name": "Seun M. Olawepo",
        "short_title": "Senior Agile & Cloud Applications Leader",
        "long_title": "Senior Agile & Cloud Applications Leader driving digital transformation through SAFe, Scrum, and enterprise delivery excellence",
        "bio": "15+ years leading multi-team Agile initiatives, mentoring high-performing teams, and delivering measurable business outcomes across cloud and enterprise systems.",
        "image": "/api/placeholder/400/400",
        "primary_cta": "View Case Studies",
        "secondary_cta": "Download Resume"
    },
    
    "about": {
        "short": "Senior IT leader specializing in Agile delivery, cloud transformation, and enterprise systems with 15+ years of experience.",
        "long": "Senior IT leader with 15+ years in Agile delivery, cloud, and enterprise systems. I specialize in guiding multi-team initiatives, mentoring high-performing teams, and bridging business and technology to deliver measurable results. My experience spans Business Analysis, Release Train Engineering, Agile Coaching, Product Ownership, and Project Management. I hold advanced certifications including PMP, PSM, CSM, SAFe RTE, and AWS Cloud Practitioner, with an M.Sc. in IT Project Management. My civil engineering background provides a unique foundation for systematic problem-solving and structured delivery approaches.",
        "key_stats": [
            {"label": "Years Experience", "value": "15+"},
            {"label": "Budget Managed", "value": "$5M+"},
            {"label": "Teams Mentored", "value": "20+"},
            {"label": "Delivery Improvement", "value": "+35%"}
        ]
    },

    "projects": [
        {
            "id": 1,
            "title": "PI Planning Excellence Playbook",
            "category": "Agile Leadership",
            "problem": "Teams were misaligned on dependencies and commitments, causing missed delivery in past increments with 200+ participants across hybrid environments.",
            "role": "Release Train Engineer & Agile Coach",
            "approach": [
                "Developed comprehensive PI Planning Playbook with agenda, roles, and deliverables",
                "Conducted pre-PI workshops to align objectives and capacity planning",
                "Facilitated 200+ participants in hybrid PI Planning sessions",
                "Created Program Board to visualize dependencies and risks using Miro"
            ],
            "outcomes": [
                "Teams committed to 95% of prioritized features",
                "Dependencies tracked in Jira improved on-time delivery by 20%",
                "Reduced mid-PI surprises and improved predictability",
                "Enhanced cross-team collaboration and alignment"
            ],
            "artifacts": ["Miro Program Board", "PI Objectives Sheet", "Playbook PDF"],
            "tags": ["SAFe", "PI Planning", "Dependencies", "2023"],
            "image": "/api/placeholder/600/400",
            "metrics": {"success_rate": "95%", "improvement": "20%", "participants": "200+"},
            "featured": True,
            "display_order": 1
        },
        {
            "id": 2,
            "title": "WSJF Prioritization Framework",
            "category": "Product Management",
            "problem": "Product backlog contained 200+ competing items with unclear stakeholder priorities, causing delivery inefficiencies and stakeholder frustration.",
            "role": "Product Owner & Business Analyst",
            "approach": [
                "Introduced Weighted Shortest Job First (WSJF) prioritization methodology",
                "Conducted stakeholder workshops for business value scoring alignment",
                "Created prioritization matrix integrated with Jira for transparency",
                "Established regular backlog refinement cadence"
            ],
            "outcomes": [
                "Reduced backlog noise by 40% through systematic prioritization",
                "High-value features delivered first, increasing stakeholder satisfaction",
                "Improved team focus and delivery predictability",
                "Enhanced business value delivery per sprint"
            ],
            "artifacts": ["WSJF Scoring Sheet", "Workshop Notes", "Jira Integration"],
            "tags": ["WSJF", "Prioritization", "Stakeholder Management", "2022"],
            "image": "/api/placeholder/600/400",
            "metrics": {"backlog_reduction": "40%", "satisfaction": "High", "items": "200+"},
            "featured": True,
            "display_order": 2
        },
        {
            "id": 3,
            "title": "Cross-Team Dependency Management",
            "category": "Release Train Engineering",
            "problem": "Unmanaged cross-team dependencies caused mid-Program Increment blockers, impacting delivery timelines and team morale.",
            "role": "Release Train Engineer",
            "approach": [
                "Implemented dependency mapping during PI Planning sessions",
                "Introduced weekly Scrum of Scrums for dependency coordination",
                "Tracked dependencies in Jira and Confluence with clear ownership and dates",
                "Created dependency risk dashboard for leadership visibility"
            ],
            "outcomes": [
                "Dependencies visible 100% by Week 2 of each PI",
                "Reduced last-minute blockers by 30%",
                "Improved team autonomy and delivery confidence",
                "Enhanced predictability across multiple ARTs"
            ],
            "artifacts": ["Dependency Dashboard", "Confluence Risk Log", "Scrum of Scrums Notes"],
            "tags": ["Dependencies", "Risk Management", "SAFe", "2022"],
            "image": "/api/placeholder/600/400",
            "metrics": {"visibility": "100%", "blocker_reduction": "30%", "teams": "Multiple ARTs"},
            "featured": True,
            "display_order": 3
        },
        {
            "id": 4,
            "title": "Continuous Integration Excellence",
            "category": "DevOps & Quality",
            "problem": "Teams delivered code inconsistently causing integration failures, with build success rate at only 70% affecting deployment frequency.",
            "role": "Scrum Master / Agile Coach",
            "approach": [
                "Advocated daily commits with automated builds in Jenkins",
                "Introduced comprehensive Definition of Done including integration tests",
                "Set up CI metrics dashboard for team visibility",
                "Coached teams on continuous integration best practices"
            ],
            "outcomes": [
                "Build success rate increased from 70% to 95%",
                "Deployment frequency doubled within 2 sprints",
                "Reduced integration conflicts and rework",
                "Improved code quality and team confidence"
            ],
            "artifacts": ["Jenkins Pipeline", "Definition of Done Checklist", "CI Metrics Dashboard"],
            "tags": ["CI/CD", "Jenkins", "Quality", "2021"],
            "image": "/api/placeholder/600/400",
            "metrics": {"build_success": "95%", "deployment_freq": "2x", "improvement": "25%"},
            "featured": False,
            "display_order": 4
        },
        {
            "id": 5,
            "title": "Executive Stakeholder Communication",
            "category": "Stakeholder Management",
            "problem": "Executives lacked visibility into progress and risks, eroding trust and causing delayed decision-making cycles.",
            "role": "Project Manager & Product Owner",
            "approach": [
                "Created bi-weekly stakeholder reports combining metrics with narrative",
                "Set up executive dashboards in Jira and Power BI",
                "Established regular demo cadence for leadership visibility",
                "Implemented escalation protocols and risk communication"
            ],
            "outcomes": [
                "Improved executive trust leading to 50% reduction in escalations",
                "Faster decision-making: average 2 days reduced to less than 1 day",
                "Enhanced transparency and predictability",
                "Stronger stakeholder relationships and buy-in"
            ],
            "artifacts": ["Executive Dashboard", "Stakeholder Newsletter", "Demo Recordings"],
            "tags": ["Communication", "Power BI", "Executive Reporting", "2021"],
            "image": "/api/placeholder/600/400",
            "metrics": {"escalation_reduction": "50%", "decision_speed": "<1 day", "trust": "High"},
            "featured": False,
            "display_order": 5
        },
        {
            "id": 6,
            "title": "Scrum Ceremonies Transformation",
            "category": "Agile Coaching",
            "problem": "Agile ceremonies were inconsistent and perceived as 'waste of time' by team members, with low participation and engagement.",
            "role": "Scrum Master",
            "approach": [
                "Standardized agendas for standups, reviews, retrospectives, and grooming",
                "Introduced timeboxing and professional facilitation techniques",
                "Rotated facilitation responsibilities to build team ownership",
                "Implemented continuous improvement based on ceremony feedback"
            ],
            "outcomes": [
                "Ceremony participation increased by 80%",
                "Retrospectives generated 3 major process improvements per PI",
                "Enhanced team engagement and ownership",
                "Improved overall Agile maturity and culture"
            ],
            "artifacts": ["Retrospective Board", "Facilitation Guide", "Ceremony Templates"],
            "tags": ["Scrum", "Facilitation", "Team Building", "2020"],
            "image": "/api/placeholder/600/400",
            "metrics": {"participation": "80%", "improvements": "3 per PI", "engagement": "High"},
            "featured": False,
            "display_order": 6
        }
    ],

    "experience": [
        {
            "id": 1,
            "company": "TSPi",
            "role": "Sr. SAFe Scrum Master/Team Lead",
            "period": "September 2023 – Present",
            "location": "Supporting USDA/NRCS projects",
            "achievements": [
                "Led Agile ceremonies and PI Planning sessions, improving team alignment, transparency, and delivery speed across multiple cross-functional teams",
                "Reduced manual data entry by 40% through cross-functional rule-based automation implementation",
                "Redesigned workflows using BPMN across four departments, reducing rework and operational delays",
                "Facilitated stakeholder interviews, workshops, and JAD sessions for business requirements gathering",
                "Aligned Agile practices with business objectives through strategic stakeholder collaboration"
            ],
            "tags": ["SAFe", "Scrum Master", "BPMN", "Process Improvement", "Government"]
        },
        {
            "id": 2,
            "company": "Fidelity Investments",
            "role": "Sr. Agile Delivery Manager & Business Rules Analyst Lead",
            "period": "January 2023 – August 2023",
            "location": "Financial Services",
            "achievements": [
                "Delivered gap analysis saving $500K annually by consolidating overlapping systems",
                "Reduced technical debt by 20% across two major sprints through requirement review checkpoints",
                "Led business rule documentation and mapping for AI/ML and rules engine integrations",
                "Supported PI Planning coordination and progress tracking in Jira",
                "Mentored teams in Agile ceremonies and delivery best practices"
            ],
            "tags": ["Financial Services", "AI/ML", "Cost Optimization", "Technical Debt", "Jira"]
        },
        {
            "id": 3,
            "company": "Fidelity Investments",
            "role": "Sr. SAFe Scrum Master/RTE",
            "period": "June 2019 – January 2023",
            "location": "Financial Services",
            "achievements": [
                "Provided expert guidance on Agile best practices, coaching Scrum Masters and Product Owners",
                "Improved iteration planning processes, reducing bug fixes by 75%",
                "Enhanced release management and ServiceNow ticket visibility through data analytics",
                "Utilized agile estimation techniques improving predictability across multiple teams",
                "Created SMART action items from sprint reviews and retrospectives"
            ],
            "tags": ["SAFe", "RTE", "Coaching", "ServiceNow", "Quality Improvement"]
        },
        {
            "id": 4,
            "company": "UnitedHealth Group",
            "role": "Sr. Agile Lead & Business Analyst Lead",
            "period": "September 2018 – May 2019",
            "location": "Healthcare",
            "achievements": [
                "Spearheaded Salesforce Service Cloud implementation across healthcare operations",
                "Reduced executive decision-making cycles from two weeks to two days via Tableau/Power BI dashboards",
                "Designed and delivered Agile training sessions for Scrum, Kanban, and SAFe methodologies",
                "Reduced bug fixes by 75% through improved iteration planning processes",
                "Translated complex business needs using MoSCOW and WSJF prioritization frameworks"
            ],
            "tags": ["Healthcare", "Salesforce", "BI Dashboards", "Training", "WSJF"]
        },
        {
            "id": 5,
            "company": "UnitedHealth Group",
            "role": "Senior Scrum Master (ART Leadership) / Product Owner",
            "period": "November 2016 – September 2018",
            "location": "Healthcare",
            "achievements": [
                "Managed Agile programs delivering AI-enabled patient analytics dashboards across multi-cloud platforms",
                "Improved care management efficiency by 22% through strategic product backlog management",
                "Enhanced cross-team collaboration using Azure DevOps pipelines and standardized Kanban workflows",
                "Led multiple Scrum teams within larger Agile Release Train ensuring SAFe principles adherence",
                "Partnered with engineering teams on technical delivery optimization"
            ],
            "tags": ["Healthcare AI", "Multi-cloud", "Azure DevOps", "Product Owner", "SAFe"]
        },
        {
            "id": 6,
            "company": "Mastercard",
            "role": "IT Agile Scrum Master & Business Rules Analyst Lead",
            "period": "March 2012 – October 2016",
            "location": "Financial Technology",
            "achievements": [
                "Facilitated global KPI tracking application delivery across international teams",
                "Increased stakeholder satisfaction scores by 28% over three quarters through alignment sessions",
                "Shortened product delivery cycles by 30% through efficient requirements gathering and Agile ceremonies",
                "Led web-based e-commerce platform development for global payment processing",
                "Mentored teams in Agile practices while managing backlogs in Azure DevOps"
            ],
            "tags": ["Global KPI", "E-commerce", "Stakeholder Management", "Azure DevOps", "FinTech"]
        }
    ],

    "skills": {
        "Agile Frameworks": [
            "SAFe (Scaled Agile Framework)",
            "Scrum",
            "Kanban", 
            "Lean Portfolio Management",
            "PI Planning",
            "Release Train Engineering"
        ],
        "Leadership & Delivery": [
            "Stakeholder Management",
            "Team Coaching & Mentoring",
            "Change Management",
            "Risk Mitigation",
            "Budget Management",
            "Portfolio Management"
        ],
        "Cloud & DevOps": [
            "AWS Cloud Practitioner",
            "Azure DevOps",
            "CI/CD Pipelines",
            "Jenkins",
            "Multi-cloud Architecture",
            "Cloud Migration"
        ],
        "Tools & Platforms": [
            "Jira",
            "Confluence",
            "ServiceNow",
            "Salesforce",
            "Power BI",
            "Tableau",
            "Miro",
            "Microsoft Visio"
        ],
        "Business Analysis": [
            "Requirements Gathering",
            "User Story Writing",
            "BPMN Process Modeling",
            "MoSCOW Prioritization",
            "WSJF Scoring",
            "Gap Analysis"
        ],
        "Technical": [
            "AI/ML Integration",
            "Business Rules Analysis",
            "API Testing (Postman)",
            "TestRail",
            "Cybersecurity GRC",
            "Pega Business Architecture"
        ]
    },

    "certifications": [
        {
            "name": "Project Management Professional (PMP)",
            "issuer": "PMI",
            "year": "2022",
            "credential_id": "Verified"
        },
        {
            "name": "Professional Scrum Master (PSM I)",
            "issuer": "Scrum.org",
            "year": "2019",
            "credential_id": "Verified"
        },
        {
            "name": "Certified ScrumMaster (CSM)",
            "issuer": "Scrum Alliance",
            "year": "2019",
            "credential_id": "Verified"
        },
        {
            "name": "SAFe Release Train Engineer (RTE)",
            "issuer": "Scaled Agile",
            "year": "2019",
            "credential_id": "Verified"
        },
        {
            "name": "AWS Cloud Practitioner",
            "issuer": "Amazon Web Services",
            "year": "2025",
            "credential_id": "Cloud Fundamentals"
        },
        {
            "name": "SAFe Product Owner / Product Manager (POPM)",
            "issuer": "Scaled Agile",
            "year": "2022",
            "credential_id": "Verified"
        },
        {
            "name": "Certified Pega Business Architect (CPBA)",
            "issuer": "Pega",
            "year": "2024",
            "credential_id": "Enterprise App Architecture"
        },
        {
            "name": "Professional Agile Leadership (PAL I)",
            "issuer": "Scrum.org",
            "year": "2023",
            "credential_id": "Verified"
        },
        {
            "name": "ServiceNow Certified System Administrator",
            "issuer": "ServiceNow",
            "year": "2022",
            "credential_id": "Verified"
        }
    ],

    "education": [
        {
            "degree": "Master of Science",
            "field": "Information Technology Project Management",
            "institution": "Northcentral University",
            "location": "San Diego, CA",
            "year": "2022",
            "details": "Specialized in IT project management methodologies and digital transformation"
        },
        {
            "degree": "Bachelor of Science",
            "field": "Civil Engineering Technology",
            "institution": "University of Ilorin",
            "location": "Ilorin, Nigeria", 
            "year": "2007",
            "details": "Foundation in systematic problem-solving and structured engineering approaches"
        }
    ],

    "contact": {
        "email": "seunolawepo2010@gmail.com",
        "linkedin": "https://www.linkedin.com/in/seun-m-o/",
        "availability": "Available 8am to 5pm CST",
        "location": "Available for Cloud Applications Manager roles",
        "cta": "Schedule 15/30 min consultation"
    }
}

async def seed_database():
    """Seed the database with portfolio data"""
    try:
        mongo_url = os.environ['MONGO_URL']
        db_name = os.environ['DB_NAME']
        
        db_manager = DatabaseManager(mongo_url, db_name)
        
        print("Starting database seeding...")
        success = await db_manager.seed_database(portfolio_data)
        
        if success:
            print("✅ Database seeded successfully!")
        else:
            print("❌ Database seeding failed!")
            
        await db_manager.close()
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")

if __name__ == "__main__":
    asyncio.run(seed_database())