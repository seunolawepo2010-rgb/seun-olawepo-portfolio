from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# Portfolio Data Models
class HeroData(BaseModel):
    name: str
    short_title: str
    long_title: str
    bio: str
    image: str
    primary_cta: str
    secondary_cta: str

class KeyStat(BaseModel):
    label: str
    value: str

class AboutData(BaseModel):
    short: str
    long: str
    key_stats: List[KeyStat]

class ProjectMetrics(BaseModel):
    success_rate: Optional[str] = None
    improvement: Optional[str] = None
    participants: Optional[str] = None
    backlog_reduction: Optional[str] = None
    satisfaction: Optional[str] = None
    items: Optional[str] = None
    visibility: Optional[str] = None
    blocker_reduction: Optional[str] = None
    teams: Optional[str] = None
    build_success: Optional[str] = None
    deployment_freq: Optional[str] = None
    escalation_reduction: Optional[str] = None
    decision_speed: Optional[str] = None
    trust: Optional[str] = None
    participation: Optional[str] = None
    engagement: Optional[str] = None

class Project(BaseModel):
    id: Optional[int] = None
    title: str
    category: str
    problem: str
    role: str
    approach: List[str]
    outcomes: List[str]
    artifacts: List[str]
    tags: List[str]
    image: str
    metrics: ProjectMetrics
    featured: bool = False
    display_order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Experience(BaseModel):
    id: Optional[int] = None
    company: str
    role: str
    period: str
    location: str
    achievements: List[str]
    tags: List[str]

class Certification(BaseModel):
    name: str
    issuer: str
    year: str
    credential_id: str

class Education(BaseModel):
    degree: str
    field: str
    institution: str
    location: str
    year: str
    details: str

class ContactInfo(BaseModel):
    email: str
    linkedin: str
    availability: str
    location: str
    cta: str

# Contact Form Models
class ContactMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    subject: str
    message: str
    availability_preference: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "new"
    ip_address: Optional[str] = None

class ContactMessageCreate(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str
    availability_preference: Optional[str] = None

# Portfolio Section Models
class PortfolioSection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section: str
    data: Dict[str, Any]
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1

# API Response Models
class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

class ProjectsResponse(BaseModel):
    projects: List[Project]
    total: int
    filtered: int

class SkillsResponse(BaseModel):
    skills: Dict[str, List[str]]

class CertificationsResponse(BaseModel):
    certifications: List[Certification]
    education: List[Education]