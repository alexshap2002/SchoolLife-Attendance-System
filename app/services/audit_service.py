"""Audit service for logging all system changes."""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def log_audit(
    db: AsyncSession,
    action_type: str,  # 'CREATE', 'UPDATE', 'DELETE', 'ENROLL', 'UNENROLL', etc.
    entity_type: str,  # 'student', 'teacher', 'club', 'schedule', 'attendance', 'payroll', etc.
    entity_id: Optional[int],
    entity_name: str,
    description: str,
    user_name: str = "Адміністратор",
    user_type: str = "admin",
    user_id: Optional[int] = None,
    changes: Optional[Dict[str, Any]] = None,
) -> Optional[AuditLog]:
    """
    Log an audit event.
    
    Args:
        db: Database session
        action_type: Type of action (CREATE, UPDATE, DELETE, etc.)
        entity_type: Type of entity (student, teacher, club, etc.)
        entity_id: ID of the entity
        entity_name: Name of the entity for quick search
        description: Human-readable description
        user_name: Name of the user who performed the action
        user_type: Type of user (admin, teacher, system)
        user_id: ID of the user (if applicable)
        changes: Dictionary with before/after changes
    
    Returns:
        Created AuditLog instance or None if failed
    """
    try:
        audit_log = AuditLog(
            timestamp=datetime.now(timezone.utc),
            user_type=user_type,
            user_id=user_id,
            user_name=user_name,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            changes_json=changes,
            # Legacy fields for compatibility
            actor=user_name,
            action=action_type,
            entity=entity_type,
            payload_json=changes,
            created_at=datetime.now(timezone.utc),
        )
        
        db.add(audit_log)
        # НЕ робимо commit тут - це зробить батьківський endpoint
        # await db.commit()
        # await db.refresh(audit_log)
        
        logger.info(f"✅ Audit log created: {action_type} {entity_type} '{entity_name}' by {user_name}")
        return audit_log
        
    except Exception as e:
        logger.error(f"❌ Failed to create audit log: {e}")
        logger.exception(e)  # Логуємо повний traceback для дебагу
        # Не падаємо якщо аудит не працює - це не критично
        # НЕ робимо rollback - це зламає батьківську транзакцію
        return None


async def get_audit_logs(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    entity_type: Optional[str] = None,
    action_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """
    Get audit logs with filters.
    
    Args:
        db: Database session
        date_from: Filter from date
        date_to: Filter to date
        entity_type: Filter by entity type
        action_type: Filter by action type
        search: Search in entity_name and description
        limit: Number of records to return
        offset: Offset for pagination
    
    Returns:
        Tuple of (list of audit logs, total count)
    """
    try:
        # Base query
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))
        
        # Filters
        filters = []
        
        if date_from:
            filters.append(AuditLog.timestamp >= date_from)
        
        if date_to:
            filters.append(AuditLog.timestamp <= date_to)
        
        if entity_type:
            filters.append(AuditLog.entity_type == entity_type)
        
        if action_type:
            filters.append(AuditLog.action_type == action_type)
        
        if search:
            search_pattern = f"%{search}%"
            filters.append(
                or_(
                    AuditLog.entity_name.ilike(search_pattern),
                    AuditLog.description.ilike(search_pattern),
                    AuditLog.user_name.ilike(search_pattern),
                )
            )
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Order by timestamp descending (newest first)
        query = query.order_by(AuditLog.timestamp.desc())
        
        # Pagination
        query = query.limit(limit).offset(offset)
        
        # Execute queries
        result = await db.execute(query)
        logs = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        return list(logs), total_count
        
    except Exception as e:
        logger.error(f"❌ Failed to get audit logs: {e}")
        return [], 0


async def delete_old_audit_logs(db: AsyncSession, days: int = 365) -> int:
    """
    Delete audit logs older than specified days (default: 1 year).
    
    Args:
        db: Database session
        days: Number of days to keep
    
    Returns:
        Number of deleted records
    """
    try:
        from datetime import timedelta
        from sqlalchemy import delete
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        result = await db.execute(
            delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
        )
        
        await db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"🗑️ Deleted {deleted_count} old audit logs (older than {days} days)")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"❌ Failed to delete old audit logs: {e}")
        await db.rollback()
        return 0

