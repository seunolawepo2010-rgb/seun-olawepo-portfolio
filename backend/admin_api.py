from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging
from models import ContactMessage, ApiResponse
from database import DatabaseManager
import os
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)

def get_db_manager():
    """Get database manager instance"""
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    return DatabaseManager(mongo_url, db_name)

@router.get("/messages")
async def get_all_contact_messages(
    status: Optional[str] = Query(None, description="Filter by status: new, read, responded"),
    limit: Optional[int] = Query(50, description="Maximum number of messages to return"),
    skip: Optional[int] = Query(0, description="Number of messages to skip")
):
    """Get contact messages with pagination and filtering"""
    try:
        db_manager = get_db_manager()
        
        # Build filter query
        filter_query = {}
        if status:
            filter_query["status"] = status
        
        # Get messages with pagination
        messages = await db_manager.db.contact_messages.find(
            filter_query, {"_id": 0}
        ).sort("submitted_at", -1).skip(skip).limit(limit).to_list(length=None)
        
        # Get total count
        total_count = await db_manager.db.contact_messages.count_documents(filter_query)
        
        return {
            "messages": messages,
            "total": total_count,
            "showing": len(messages),
            "skip": skip,
            "limit": limit,
            "has_more": (skip + len(messages)) < total_count
        }
    except Exception as e:
        logger.error(f"Error getting contact messages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/messages/{message_id}/status")
async def update_message_status(
    message_id: str,
    new_status: str = Query(..., description="New status: new, read, responded")
):
    """Update the status of a contact message"""
    try:
        db_manager = get_db_manager()
        
        valid_statuses = ["new", "read", "responded"]
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )
        
        result = await db_manager.db.contact_messages.update_one(
            {"id": message_id},
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {
            "success": True,
            "message": f"Message status updated to '{new_status}'",
            "message_id": message_id,
            "new_status": new_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating message status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/messages/{message_id}")
async def delete_message(message_id: str):
    """Delete a contact message"""
    try:
        db_manager = get_db_manager()
        
        result = await db_manager.db.contact_messages.delete_one({"id": message_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {
            "success": True,
            "message": "Message deleted successfully",
            "message_id": message_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        db_manager = get_db_manager()
        
        # Get message counts by status
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        
        status_counts = await db_manager.db.contact_messages.aggregate(pipeline).to_list(length=None)
        
        # Get recent messages (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_count = await db_manager.db.contact_messages.count_documents({
            "submitted_at": {"$gte": week_ago}
        })
        
        # Get total messages
        total_messages = await db_manager.db.contact_messages.count_documents({})
        
        # Format status counts
        status_summary = {}
        for item in status_counts:
            status_summary[item["_id"]] = item["count"]
        
        # Ensure all statuses are represented
        for status in ["new", "read", "responded"]:
            if status not in status_summary:
                status_summary[status] = 0
        
        return {
            "total_messages": total_messages,
            "recent_messages_7_days": recent_count,
            "status_breakdown": status_summary,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/messages/export")
async def export_messages():
    """Export all contact messages as JSON"""
    try:
        db_manager = get_db_manager()
        
        messages = await db_manager.db.contact_messages.find(
            {}, {"_id": 0}
        ).sort("submitted_at", -1).to_list(length=None)
        
        return {
            "export_date": datetime.utcnow().isoformat(),
            "total_messages": len(messages),
            "messages": messages
        }
        
    except Exception as e:
        logger.error(f"Error exporting messages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")