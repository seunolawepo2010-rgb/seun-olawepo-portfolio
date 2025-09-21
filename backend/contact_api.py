from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
import logging
from models import ContactMessage, ContactMessageCreate, ApiResponse
from database import DatabaseManager
from email_service import EmailService
import os
from datetime import datetime

router = APIRouter(prefix="/api/contact", tags=["contact"])
logger = logging.getLogger(__name__)

def get_db_manager():
    """Get database manager instance"""
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    return DatabaseManager(mongo_url, db_name)

# Initialize email service
email_service = EmailService()

@router.post("/message", response_model=ApiResponse)
async def submit_contact_message(message_data: ContactMessageCreate, request: Request):
    """Submit a contact form message"""
    try:
        db_manager = get_db_manager()
        # Get client IP
        client_ip = request.client.host
        
        # Create contact message
        contact_message = ContactMessage(
            name=message_data.name,
            email=message_data.email,
            subject=message_data.subject,
            message=message_data.message,
            availability_preference=message_data.availability_preference,
            ip_address=client_ip
        )
        
        # Store in database
        success = await db_manager.create_contact_message(contact_message)
        
        if success:
            logger.info(f"Contact message submitted by {message_data.email}")
            
            # Send email notification
            email_sent = await email_service.send_contact_notification(contact_message.dict())
            if email_sent:
                logger.info("📧 Email notification sent successfully")
            else:
                logger.warning("⚠️ Failed to send email notification, but message was saved")
            
            return ApiResponse(
                success=True,
                message="Your message has been sent successfully! I'll get back to you within 24 hours.",
                data={
                    "message_id": contact_message.id,
                    "email_notification": email_sent
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to send message")
            
    except Exception as e:
        logger.error(f"Error submitting contact message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/messages")
async def get_contact_messages(status: Optional[str] = None):
    """Get contact messages (admin endpoint)"""
    try:
        db_manager = get_db_manager()
        messages = await db_manager.get_contact_messages(status=status)
        return {
            "messages": messages,
            "total": len(messages)
        }
    except Exception as e:
        logger.error(f"Error getting contact messages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/info")
async def get_contact_info():
    """Get contact information"""
    try:
        db_manager = get_db_manager()
        contact_data = await db_manager.get_portfolio_section("contact")
        if not contact_data:
            raise HTTPException(status_code=404, detail="Contact data not found")
        return contact_data
    except Exception as e:
        logger.error(f"Error getting contact info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")