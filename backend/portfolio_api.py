from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
import logging
from models import (
    HeroData, AboutData, Project, Experience, ContactMessage, 
    ContactMessageCreate, ApiResponse, ProjectsResponse, 
    SkillsResponse, CertificationsResponse
)
from database import DatabaseManager
import os

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])
logger = logging.getLogger(__name__)

# Database connection
def get_db_manager():
    """Get database manager instance"""
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    return DatabaseManager(mongo_url, db_name)

@router.get("/hero")
async def get_hero_data():
    """Get hero section data"""
    try:
        db_manager = get_db_manager()
        hero_data = await db_manager.get_portfolio_section("hero")
        if not hero_data:
            raise HTTPException(status_code=404, detail="Hero data not found")
        return hero_data
    except Exception as e:
        logger.error(f"Error getting hero data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/about")
async def get_about_data():
    """Get about section data"""
    try:
        db_manager = get_db_manager()
        about_data = await db_manager.get_portfolio_section("about")
        if not about_data:
            raise HTTPException(status_code=404, detail="About data not found")
        return about_data
    except Exception as e:
        logger.error(f"Error getting about data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/projects", response_model=ProjectsResponse)
async def get_projects(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    limit: Optional[int] = None
):
    """Get projects with optional filtering"""
    try:
        db_manager = get_db_manager()
        projects = await db_manager.get_projects(category=category, tag=tag, limit=limit)
        total_projects = await db_manager.get_projects()
        
        return ProjectsResponse(
            projects=projects,
            total=len(total_projects),
            filtered=len(projects)
        )
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/experience")
async def get_experience():
    """Get work experience data"""
    try:
        db_manager = get_db_manager()
        experience = await db_manager.get_experience()
        return experience
    except Exception as e:
        logger.error(f"Error getting experience: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/skills", response_model=SkillsResponse)
async def get_skills():
    """Get skills data"""
    try:
        db_manager = get_db_manager()
        skills_data = await db_manager.get_portfolio_section("skills")
        if not skills_data:
            raise HTTPException(status_code=404, detail="Skills data not found")
        return SkillsResponse(skills=skills_data)
    except Exception as e:
        logger.error(f"Error getting skills: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/certifications", response_model=CertificationsResponse)
async def get_certifications():
    """Get certifications and education data"""
    try:
        db_manager = get_db_manager()
        cert_data = await db_manager.get_portfolio_section("certifications")
        if not cert_data:
            raise HTTPException(status_code=404, detail="Certifications data not found")
        return CertificationsResponse(
            certifications=cert_data["certifications"],
            education=cert_data["education"]
        )
    except Exception as e:
        logger.error(f"Error getting certifications: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/contact")
async def get_contact_info():
    """Get contact information"""
    try:
        db_manager = get_db_manager()
        contact_data = await db_manager.get_portfolio_section("contact")
        if not contact_data:
            raise HTTPException(status_code=404, detail="Contact data not found")
        return contact_data
    except Exception as e:
        logger.error(f"Error getting contact data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")