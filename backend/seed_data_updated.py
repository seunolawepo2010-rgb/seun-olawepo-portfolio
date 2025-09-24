import asyncio
import json
import os
import sys
from database import DatabaseManager
from datetime import datetime

# Mock data (updated with new images and content)
portfolio_data = {
    "hero": {
        "name": "Seun M. Olawepo",
        "short_title": "Senior Agile & Cloud Leader | InfoSec GRC Analyst | AI Generalist",
        "long_title": "Senior Agile & Cloud Application Leader | InfoSec GRC Analyst driving digital transformation through SAFe, Scrum, AI/ML integration, cybersecurity governance, and enterprise delivery excellence",
        "bio": "15+ years leading multi-team Agile initiatives, cybersecurity governance & compliance programs, mentoring high-performing teams, and delivering measurable business outcomes across cloud, AI/ML, and enterprise systems.",
        "image": "https://customer-assets.emergentagent.com/job_agile-portfolio/artifacts/dn6w3qoh_55555.jpeg",
        "primary_cta": "View Case Studies",
        "secondary_cta": "Download Resume"
    },
    
    "about": {
        "short": "Senior IT leader specializing in Agile delivery, cybersecurity governance & risk management, cloud transformation, AI/ML integration, and enterprise systems with 15+ years of experience.",
        "long": "Senior IT leader with 15+ years in Agile delivery, cybersecurity governance & compliance, cloud, AI/ML, and enterprise systems. I specialize in guiding multi-team initiatives, implementing robust GRC frameworks, mentoring high-performing teams, and bridging business and technology to deliver measurable results. My experience spans Business Analysis, Release Train Engineering, Agile Coaching, Product Ownership, Project Management, InfoSec GRC Analysis, and AI/ML solution implementation. I hold advanced certifications including CISM, CISA, PMP, PSM, CSM, SAFe RTE, and AWS Cloud Practitioner, with an M.Sc. in IT Project Management. My civil engineering background provides a unique foundation for systematic problem-solving and structured delivery approaches, while my AI/ML and cybersecurity expertise enables data-driven decision making and intelligent automation solutions.",
        "key_stats": [
            {"label": "Years Experience", "value": "15+"},
            {"label": "Budget Managed", "value": "$5M+"},
            {"label": "Teams Mentored", "value": "200+"},
            {"label": "Delivery Improvement", "value": "+35%"}
        ]
    },

    "projects": [
        {
            "id": 1,
            "title": "Enterprise PI Planning Excellence Framework",
            "category": "Agile Leadership",
            "problem": "A Fortune 500 financial services organization with 200+ participants across 12 Agile Release Trains was experiencing misaligned dependencies and commitments, causing 35% delivery shortfall in past increments. Hybrid teams across 5 time zones struggled with coordination, resulting in $2.3M in delayed feature releases.",
            "role": "Lead Release Train Engineer & Agile Transformation Coach",
            "approach": [
                "Designed and implemented comprehensive PI Planning Playbook with standardized agenda, roles, RACI matrix, and measurable deliverables",
                "Conducted pre-PI readiness workshops integrating capacity planning with AI-powered sprint velocity predictions",
                "Facilitated 200+ participants across hybrid environments using advanced digital collaboration tools and real-time dependency visualization",
                "Created interactive Program Board with automated dependency tracking, risk assessment algorithms, and commitment confidence scoring",
                "Integrated ML-driven predictive analytics to forecast potential blockers and optimize feature prioritization using WSJF methodology"
            ],
            "outcomes": [
                "Achieved 95% feature commitment success rate, improving from previous 65% baseline",
                "Dependencies tracked and resolved in Jira with automated notifications, improving on-time delivery by 20%",
                "Reduced mid-PI scope changes by 40% through better upfront planning and stakeholder alignment",
                "Enhanced cross-team collaboration resulting in 25% faster issue resolution",
                "Established repeatable framework adopted across 8 additional ARTs within 6 months"
            ],
            "artifacts": ["PI Planning Playbook (47 pages)", "Program Board Template", "Dependency Risk Assessment Matrix", "Stakeholder Communication Plan"],
            "tags": ["SAFe", "PI Planning", "Enterprise Transformation", "ML Analytics", "2023"],
            "image": "https://images.pexels.com/photos/7213435/pexels-photo-7213435.jpeg",
            "metrics": {"success_rate": "95%", "improvement": "20%", "participants": "200+", "cost_savings": "$2.3M"},
            "featured": True,
            "display_order": 1
        },
        {
            "id": 2,
            "title": "AI-Enhanced WSJF Prioritization System",
            "category": "Product Management",
            "problem": "Healthcare technology company's product backlog contained 350+ competing user stories across 4 product lines with unclear ROI visibility and stakeholder priorities. Product owners spent 40% of their time in prioritization debates, delaying sprint planning and reducing development velocity by 30%.",
            "role": "Senior Product Owner & AI Solutions Architect",
            "approach": [
                "Implemented Weighted Shortest Job First (WSJF) prioritization methodology with AI-powered business value scoring",
                "Conducted stakeholder alignment workshops using collaborative decision-making frameworks and data-driven consensus building",
                "Developed automated prioritization matrix in Jira integrated with business intelligence dashboards for real-time ROI tracking",
                "Created machine learning model analyzing historical delivery data to predict effort estimation accuracy and success probability",
                "Established regular backlog refinement cadence with AI-assisted story splitting and acceptance criteria optimization"
            ],
            "outcomes": [
                "Reduced backlog complexity by 40% through systematic AI-driven prioritization and story consolidation",
                "High-value features delivered first, increasing customer satisfaction scores by 28% and reducing churn by 15%",
                "Improved development team focus and delivery predictability, achieving 92% sprint goal completion rate",
                "Enhanced business value delivery per sprint by 35% through optimized story sequencing and dependency management",
                "Established data-driven product decision framework adopted company-wide across 6 product teams"
            ],
            "artifacts": ["WSJF Calculator with ML Integration", "Stakeholder Workshop Templates", "ROI Tracking Dashboard", "Prioritization Playbook"],
            "tags": ["WSJF", "AI/ML", "Prioritization", "Product Strategy", "2022"],
            "image": "https://images.unsplash.com/photo-1666875753105-c63a6f3bdc86?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Njd8MHwxfHNlYXJjaHwxfHxkYXRhJTIwYW5hbHl0aWNzfGVufDB8fHx8MTc1ODQ4Mjc4N3ww&ixlib=rb-4.1.0&q=85",
            "metrics": {"backlog_reduction": "40%", "satisfaction": "28%", "sprint_success": "92%", "roi_improvement": "35%"},
            "featured": True,
            "display_order": 2
        },
        {
            "id": 3,
            "title": "Intelligent Cross-Team Dependency Management Platform",
            "category": "Release Train Engineering",
            "problem": "Multi-national technology corporation with 15 Agile Release Trains and 120+ development teams experienced unmanaged cross-team dependencies causing 45% of Program Increments to miss delivery targets. Critical blockers emerged in weeks 8-10 of 12-week PIs, resulting in $4.2M quarterly revenue impact.",
            "role": "Enterprise Release Train Engineer & Systems Integration Lead",
            "approach": [
                "Implemented comprehensive dependency mapping framework during PI Planning with real-time visualization and impact analysis",
                "Introduced weekly Scrum of Scrums enhanced with AI-powered dependency prediction and automated escalation protocols",
                "Created integrated tracking system in Jira and Confluence with machine learning algorithms for risk assessment and mitigation recommendations",
                "Developed predictive analytics dashboard providing leadership with forward-looking dependency health metrics and early warning indicators",
                "Established cross-functional dependency review boards with automated workflow orchestration and stakeholder notification systems"
            ],
            "outcomes": [
                "Achieved 100% dependency visibility by Week 2 of each PI through automated tracking and intelligent classification",
                "Reduced critical last-minute blockers by 30% using predictive analytics and proactive mitigation strategies",
                "Improved team autonomy by 25% through better dependency planning and reduced cross-team waiting time",
                "Enhanced delivery predictability across 15 ARTs with 85% on-time delivery rate improvement",
                "Created scalable dependency management framework deployed across 200+ teams in 18 months"
            ],
            "artifacts": ["Dependency Visualization Dashboard", "Risk Assessment Algorithm", "Scrum of Scrums Playbook", "Escalation Workflow Automation"],
            "tags": ["Dependencies", "Risk Management", "SAFe", "Predictive Analytics", "2022"],
            "image": "https://images.unsplash.com/photo-1600880292089-90a7e086ee0c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzZ8MHwxfHNlYXJjaHwxfHx0ZWFtJTIwY29sbGFib3JhdGlvbnxlbnwwfHx8fDE3NTg0NDE0Mjh8MA&ixlib=rb-4.1.0&q=85",
            "metrics": {"visibility": "100%", "blocker_reduction": "30%", "autonomy_improvement": "25%", "delivery_rate": "85%"},
            "featured": True,
            "display_order": 3
        },
        {
            "id": 4,
            "title": "AI-Driven Continuous Integration Excellence Platform",
            "category": "DevOps & Quality",
            "problem": "Enterprise software company with 50+ development teams struggled with inconsistent code delivery practices, experiencing 70% build success rate and integration failures costing 25 developer hours per week. Manual testing bottlenecks delayed releases by average 3.5 days per sprint.",
            "role": "DevOps Transformation Lead & CI/CD Solutions Architect",
            "approach": [
                "Advocated and implemented daily commits strategy with automated builds in Jenkins enhanced by AI-powered code quality analysis",
                "Introduced comprehensive Definition of Done including automated integration tests, security scans, and ML-driven performance predictions",
                "Set up intelligent CI metrics dashboard with predictive failure analysis and automated developer feedback loops",
                "Coached 50+ teams on continuous integration best practices using AI-assisted code review and automated compliance checking",
                "Implemented machine learning models for build optimization, test case prioritization, and deployment risk assessment"
            ],
            "outcomes": [
                "Build success rate increased from 70% to 95% through intelligent failure prediction and automated remediation",
                "Deployment frequency doubled within 2 sprints using AI-optimized pipeline orchestration and risk-based testing",
                "Reduced integration conflicts by 65% through intelligent merge conflict prediction and automated resolution suggestions",
                "Improved overall code quality metrics by 40% using ML-driven technical debt identification and prioritization",
                "Established center of excellence for CI/CD practices adopted across 12 business units and 200+ applications"
            ],
            "artifacts": ["Jenkins AI Pipeline Templates", "Quality Gates Framework", "CI Metrics Analytics Platform", "Developer Coaching Materials"],
            "tags": ["CI/CD", "Jenkins", "Quality Engineering", "AI/ML", "2021"],
            "image": "https://images.unsplash.com/photo-1631624210938-539575f92e3c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzV8MHwxfHNlYXJjaHw0fHxkZXZvcHN8ZW58MHx8fHwxNzU4NDgyNzk4fDA&ixlib=rb-4.1.0&q=85",
            "metrics": {"build_success": "95%", "deployment_freq": "2x", "conflict_reduction": "65%", "quality_improvement": "40%"},
            "featured": False,
            "display_order": 4
        },
        {
            "id": 5,
            "title": "Executive Stakeholder Intelligence Communication System",
            "category": "Stakeholder Management",
            "problem": "Global consulting firm's executives across 8 countries lacked real-time visibility into 25+ concurrent project portfolios valued at $15M, experiencing delayed decision-making cycles averaging 14 days and eroding stakeholder trust leading to 3 major client escalations per quarter.",
            "role": "Enterprise Program Manager & Executive Communications Lead",
            "approach": [
                "Created intelligent bi-weekly stakeholder reports combining quantitative metrics with AI-generated narrative insights and trend analysis",
                "Designed executive dashboards in Jira and Power BI with machine learning-powered predictive analytics and risk scoring algorithms",
                "Established regular demo cadence with automated executive briefings, stakeholder impact analysis, and ROI tracking mechanisms",
                "Implemented AI-driven escalation protocols with sentiment analysis, stakeholder communication optimization, and automated follow-up workflows",
                "Developed predictive stakeholder engagement models using historical communication data and outcome correlation analysis"
            ],
            "outcomes": [
                "Improved executive confidence and trust leading to 50% reduction in escalations through proactive transparent communication",
                "Accelerated decision-making cycles from 14 days to less than 1 day using real-time dashboards and predictive insights",
                "Enhanced strategic alignment and predictability across 25+ concurrent projects with 90% stakeholder satisfaction scores",
                "Strengthened stakeholder relationships resulting in 3 additional $2M+ contract extensions and improved client retention",
                "Created stakeholder communication excellence framework adopted across 15 global offices and 100+ client engagements"
            ],
            "artifacts": ["Executive Dashboard Suite", "Stakeholder Communication Playbook", "ROI Analytics Platform", "Demo Automation Framework"],
            "tags": ["Executive Communication", "Power BI", "Stakeholder Management", "AI Analytics", "2021"],
            "image": "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzB8MHwxfHNlYXJjaHwyfHxleGVjdXRpdmUlMjBtZWV0aW5nfGVufDB8fHx8MTc1ODQ4MjgwNHww&ixlib=rb-4.1.0&q=85",
            "metrics": {"escalation_reduction": "50%", "decision_speed": "<1 day", "satisfaction": "90%", "contract_value": "$6M+"},
            "featured": False,
            "display_order": 5
        },
        {
            "id": 6,
            "title": "AI-Enhanced Scrum Ceremonies Transformation Framework",
            "category": "Agile Coaching",
            "problem": "Technology startup with 20+ Scrum teams across 4 countries experienced inconsistent ceremony execution with 45% team member participation rates, ceremonies perceived as 'time waste' by 60% of developers, and retrospectives generating minimal actionable improvements (averaging 0.8 improvements per PI).",
            "role": "Senior Agile Coach & Organizational Transformation Lead",
            "approach": [
                "Standardized ceremony agendas with AI-powered facilitation support, timeboxing algorithms, and engagement optimization techniques",
                "Introduced professional facilitation frameworks enhanced by natural language processing for sentiment analysis and participation tracking",
                "Implemented rotational facilitation responsibilities with AI-assisted coaching recommendations and skill development tracking",
                "Created continuous improvement analytics using machine learning to identify ceremony effectiveness patterns and optimization opportunities",
                "Developed intelligent retrospective analysis tools generating data-driven action items and tracking implementation success rates"
            ],
            "outcomes": [
                "Ceremony participation increased by 80% through engaging formats and AI-powered personalization of content and delivery",
                "Retrospectives generated average of 3 major process improvements per PI with 85% implementation success rate",
                "Enhanced team engagement and psychological safety scores improved by 45% across all participating teams",
                "Improved overall Agile maturity index by 60% with sustained cultural transformation and continuous learning mindset",
                "Established Scrum excellence center of practice supporting 50+ teams and training 200+ Scrum practitioners annually"
            ],
            "artifacts": ["Ceremony Excellence Playbook", "AI Facilitation Tools", "Retrospective Analytics Platform", "Team Maturity Assessment Framework"],
            "tags": ["Scrum", "Facilitation", "Team Development", "AI/ML", "2020"],
            "image": "https://images.unsplash.com/photo-1521737852567-6949f3f9f2b5?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzZ8MHwxfHNlYXJjaHwzfHx0ZWFtJTIwY29sbGFib3JhdGlvbnxlbnwwfHx8fDE3NTg0NDE0Mjh8MA&ixlib=rb-4.1.0&q=85",
            "metrics": {"participation": "80%", "improvements": "3 per PI", "engagement": "45%", "maturity": "60%"},
            "featured": False,
            "display_order": 6
        },
        {
            "id": 7,
            "title": "Enterprise Cybersecurity GRC Framework Implementation",
            "category": "Information Security",
            "problem": "Fortune 500 financial services organization faced complex regulatory landscape with NIST, FFIEC, GLBA, NYDFS, SOX, and PCI-DSS requirements across 50+ business units. Fragmented compliance processes resulted in 40% audit findings, $2.1M in regulatory fines, and 6-month delayed product launches due to security compliance gaps.",
            "role": "Senior InfoSec GRC Analyst & Compliance Framework Architect",
            "approach": [
                "Implemented comprehensive NIST Cybersecurity Framework with integrated FAIR risk assessment methodology across enterprise architecture",
                "Developed automated GRC platform using ServiceNow and Archer with AI-powered control testing, gap analysis, and regulatory mapping capabilities",
                "Established cross-functional governance committees with standardized risk scoring algorithms, third-party risk assessment protocols, and data classification frameworks",
                "Created intelligent compliance monitoring dashboard with predictive analytics for regulatory change impact assessment and proactive remediation planning",
                "Designed SOC 2 Type II readiness program with automated evidence collection, continuous control monitoring, and ML-driven anomaly detection systems"
            ],
            "outcomes": [
                "Achieved 95% reduction in audit findings through systematic control implementation and continuous monitoring automation",
                "Successfully passed SOC 2 Type II audit with zero exceptions, enabling $15M+ in new enterprise client contracts",
                "Reduced regulatory compliance costs by 60% through process automation, standardization, and intelligent risk prioritization",
                "Implemented HITRUST and ISO27001 frameworks resulting in industry-leading security posture and competitive differentiation",
                "Established enterprise-wide security culture with 90% employee compliance training completion and zero security incidents over 18 months"
            ],
            "artifacts": ["NIST Implementation Roadmap", "GRC Automation Platform", "Risk Assessment Matrix", "SOC 2 Compliance Package", "Security Policy Framework"],
            "tags": ["NIST Framework", "SOC 2", "GRC", "Risk Management", "Compliance", "2023"],
            "image": "https://images.unsplash.com/photo-1563013544-824ae1b704d3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzZ8MHwxfHNlYXJjaHwxfHxjeWJlcnNlY3VyaXR5fGVufDB8fHx8MTc1ODQ4Mjg3MHww&ixlib=rb-4.1.0&q=85",
            "metrics": {"audit_improvement": "95%", "cost_reduction": "60%", "contract_value": "$15M+", "zero_incidents": "18 months"},
            "featured": True,
            "display_order": 7
        }
    ],

    # ... continuing with rest of the data structure
    "experience": [
        {
            "id": 1,
            "company": "TSPi",
            "role": "Sr. SAFe Scrum Master/Team Lead",
            "period": "September 2023 – Present",
            "location": "Supporting USDA/NRCS projects",
            "achievements": [
                "Led Agile ceremonies and PI Planning sessions, improving team alignment, transparency, and delivery speed across multiple cross-functional teams",
                "Reduced manual data entry by 40% through cross-functional rule-based automation and AI-powered process optimization implementation",
                "Redesigned workflows using BPMN across four departments, integrating ML-driven decision points to reduce rework and operational delays",
                "Facilitated stakeholder interviews, workshops, and JAD sessions for business requirements gathering, incorporating AI/ML solution feasibility assessments",
                "Aligned Agile practices with business objectives through strategic stakeholder collaboration and data-driven insights from predictive analytics"
            ],
            "tags": ["SAFe", "Scrum Master", "BPMN", "Process Improvement", "Government", "AI/ML Integration"]
        }
        # ... rest of experience data would continue here
    ],

    "skills": {
        "AI/ML & Data Analytics": [
            "Machine Learning Pipeline Development",
            "Predictive Analytics & Forecasting",
            "Natural Language Processing (NLP)",
            "AI-Powered Process Optimization",
            "Business Intelligence & Data Visualization",
            "Intelligent Automation & Decision Support"
        ],
        "Agile Frameworks": [
            "SAFe (Scaled Agile Framework)",
            "Scrum",
            "Kanban", 
            "Lean Portfolio Management",
            "PI Planning",
            "Release Train Engineering"
        ]
        # ... rest of skills would continue here
    },

    "certifications": [
        {
            "name": "Project Management Professional (PMP)",
            "issuer": "PMI",
            "year": "2022",
            "credential_id": "Verified"
        }
        # ... rest of certifications
    ],

    "education": [
        {
            "degree": "Master of Science",
            "field": "Information Technology Project Management",
            "institution": "Northcentral University",
            "location": "San Diego, CA",
            "year": "2022",
            "details": "Specialized in IT project management methodologies and digital transformation"
        }
        # ... rest of education
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
    """Seed the database with updated portfolio data"""
    try:
        mongo_url = os.environ['MONGO_URL']
        db_name = os.environ['DB_NAME']
        
        db_manager = DatabaseManager(mongo_url, db_name)
        
        print("Starting database seeding with updated content...")
        success = await db_manager.seed_database(portfolio_data)
        
        if success:
            print("✅ Database seeded successfully with updated images and content!")
        else:
            print("❌ Database seeding failed!")
            
        await db_manager.close()
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")

if __name__ == "__main__":
    asyncio.run(seed_database())