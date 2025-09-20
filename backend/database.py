from motor.motor_asyncio import AsyncIOMotorClient
import os
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from models import Project, Experience, Certification, Education, ContactMessage, PortfolioSection

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, mongo_url: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        
    async def close(self):
        self.client.close()
    
    # Portfolio Data Operations
    async def get_portfolio_section(self, section: str) -> Optional[Dict[str, Any]]:
        """Get portfolio section data"""
        try:
            result = await self.db.portfolio_data.find_one({"section": section})
            return result["data"] if result else None
        except Exception as e:
            logger.error(f"Error getting portfolio section {section}: {e}")
            return None
    
    async def update_portfolio_section(self, section: str, data: Dict[str, Any]) -> bool:
        """Update portfolio section data"""
        try:
            await self.db.portfolio_data.update_one(
                {"section": section},
                {
                    "$set": {
                        "data": data,
                        "last_updated": datetime.utcnow(),
                        "version": {"$inc": 1}
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating portfolio section {section}: {e}")
            return False
    
    # Projects Operations
    async def get_projects(self, category: Optional[str] = None, tag: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get projects with optional filtering"""
        try:
            filter_query = {}
            if category:
                filter_query["category"] = category
            if tag:
                filter_query["tags"] = {"$in": [tag]}
            
            cursor = self.db.projects.find(filter_query).sort("display_order", 1)
            if limit:
                cursor = cursor.limit(limit)
                
            projects = await cursor.to_list(length=None)
            return projects
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []
    
    async def create_project(self, project: Project) -> bool:
        """Create a new project"""
        try:
            project_dict = project.dict()
            await self.db.projects.insert_one(project_dict)
            return True
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return False
    
    # Experience Operations
    async def get_experience(self) -> List[Dict[str, Any]]:
        """Get all work experience"""
        try:
            experience = await self.db.experience.find({}, {"_id": 0}).sort("id", 1).to_list(length=None)
            return experience
        except Exception as e:
            logger.error(f"Error getting experience: {e}")
            return []
    
    # Contact Operations
    async def create_contact_message(self, message: ContactMessage) -> bool:
        """Store contact form submission"""
        try:
            message_dict = message.dict()
            await self.db.contact_messages.insert_one(message_dict)
            return True
        except Exception as e:
            logger.error(f"Error creating contact message: {e}")
            return False
    
    async def get_contact_messages(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get contact messages"""
        try:
            filter_query = {"status": status} if status else {}
            messages = await self.db.contact_messages.find(filter_query).sort("submitted_at", -1).to_list(length=None)
            return messages
        except Exception as e:
            logger.error(f"Error getting contact messages: {e}")
            return []
    
    # Seeding Operations
    async def seed_database(self, portfolio_data: Dict[str, Any]) -> bool:
        """Seed database with initial portfolio data"""
        try:
            # Clear existing data
            await self.db.portfolio_data.delete_many({})
            await self.db.projects.delete_many({})
            await self.db.experience.delete_many({})
            
            # Insert hero data
            await self.db.portfolio_data.insert_one({
                "section": "hero",
                "data": portfolio_data["hero"],
                "last_updated": datetime.utcnow(),
                "version": 1
            })
            
            # Insert about data
            await self.db.portfolio_data.insert_one({
                "section": "about", 
                "data": portfolio_data["about"],
                "last_updated": datetime.utcnow(),
                "version": 1
            })
            
            # Insert skills data
            await self.db.portfolio_data.insert_one({
                "section": "skills",
                "data": portfolio_data["skills"],
                "last_updated": datetime.utcnow(),
                "version": 1
            })
            
            # Insert certifications data
            await self.db.portfolio_data.insert_one({
                "section": "certifications",
                "data": {
                    "certifications": portfolio_data["certifications"],
                    "education": portfolio_data["education"]
                },
                "last_updated": datetime.utcnow(),
                "version": 1
            })
            
            # Insert contact data
            await self.db.portfolio_data.insert_one({
                "section": "contact",
                "data": portfolio_data["contact"],
                "last_updated": datetime.utcnow(),
                "version": 1
            })
            
            # Insert projects
            for project in portfolio_data["projects"]:
                await self.db.projects.insert_one(project)
            
            # Insert experience
            for exp in portfolio_data["experience"]:
                await self.db.experience.insert_one(exp)
            
            logger.info("Database seeded successfully")
            return True
        except Exception as e:
            logger.error(f"Error seeding database: {e}")
            return False