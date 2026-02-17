"""
Admin Router - For viewing database users (development/testing only)

⚠️ WARNING: This should be protected with authentication in production!
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from ..database import get_db
from ..models.user import User
from ..schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get("/users", response_model=List[UserResponse])
async def list_all_users(db: Session = Depends(get_db)):
    """
    List all registered users (for admin/testing purposes)
    
    ⚠️ WARNING: In production, this should require admin authentication!
    """
    try:
        users = db.query(User).all()
        logger.info(f"📊 Retrieved {len(users)} users from database")
        return users
    except Exception as e:
        logger.error(f"❌ Error retrieving users: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")


@router.get("/users/count")
async def count_users(db: Session = Depends(get_db)):
    """
    Get total number of registered users
    """
    try:
        count = db.query(User).count()
        logger.info(f"📊 Total users in database: {count}")
        return {
            "total_users": count,
            "message": f"Database contains {count} registered user(s)"
        }
    except Exception as e:
        logger.error(f"❌ Error counting users: {e}")
        raise HTTPException(status_code=500, detail="Failed to count users")


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    """
    Get a specific user by ID
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user")
