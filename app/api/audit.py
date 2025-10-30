"""Audit log API endpoints."""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.models.audit_log import AuditLog
from app.api.dependencies import get_db

router = APIRouter(prefix="/api/audit", tags=["audit"])


# === PYDANTIC MODELS ===

class AuditLogResponse(BaseModel):
    """Response model for audit log."""
    id: int
    timestamp: datetime
    user_name: str
    action_type: str
    entity_type: str
    entity_id: Optional[int] = None
    entity_name: Optional[str] = None
    description: str
    changes_json: Optional[dict] = None

    class Config:
        from_attributes = True


class AuditLogsListResponse(BaseModel):
    """Response model for audit logs list with pagination."""
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# === ENDPOINTS ===

@router.get("/logs", response_model=AuditLogsListResponse)
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by entity name or description"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
):
    """Get audit logs with filters and pagination."""
    
    # Базовий запит
    query = select(AuditLog)
    
    # Фільтри
    filters = []
    
    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                AuditLog.entity_name.ilike(search_pattern),
                AuditLog.description.ilike(search_pattern),
                AuditLog.user_name.ilike(search_pattern)
            )
        )
    
    if action_type:
        filters.append(AuditLog.action_type == action_type)
    
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    
    if date_from:
        filters.append(AuditLog.timestamp >= date_from)
    
    if date_to:
        # Додаємо 1 день, щоб включити весь день
        date_to_end = date_to + timedelta(days=1)
        filters.append(AuditLog.timestamp < date_to_end)
    
    if filters:
        query = query.where(*filters)
    
    # Сортування за датою (нові спочатку)
    query = query.order_by(AuditLog.timestamp.desc())
    
    # Підрахунок загальної кількості
    count_query = select(func.count()).select_from(AuditLog)
    if filters:
        count_query = count_query.where(*filters)
    
    result = await db.execute(count_query)
    total = result.scalar()
    
    # Пагінація
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Виконання запиту
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Підрахунок кількості сторінок
    total_pages = (total + page_size - 1) // page_size
    
    return AuditLogsListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log_detail(
    log_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific audit log entry."""
    result = await db.execute(
        select(AuditLog).where(AuditLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )
    
    return AuditLogResponse.model_validate(log)


@router.delete("/logs/old")
async def delete_old_logs(
    days: int = Query(365, ge=30, le=3650, description="Delete logs older than this many days"),
    db: AsyncSession = Depends(get_db)
):
    """Delete audit logs older than specified number of days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Підрахунок кількості записів для видалення
    count_query = select(func.count()).select_from(AuditLog).where(AuditLog.timestamp < cutoff_date)
    result = await db.execute(count_query)
    count_to_delete = result.scalar()
    
    # Видалення старих записів
    from sqlalchemy import delete
    stmt = delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
    await db.execute(stmt)
    await db.commit()
    
    return {
        "success": True,
        "deleted_count": count_to_delete,
        "cutoff_date": cutoff_date.isoformat(),
        "message": f"Видалено {count_to_delete} записів старіших за {days} днів"
    }


@router.get("/stats")
async def get_audit_stats(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Statistics for last N days")
):
    """Get audit log statistics."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Загальна кількість записів
    total_query = select(func.count()).select_from(AuditLog).where(AuditLog.timestamp >= cutoff_date)
    result = await db.execute(total_query)
    total_logs = result.scalar()
    
    # Кількість по типах дій
    actions_query = (
        select(AuditLog.action_type, func.count(AuditLog.id))
        .where(AuditLog.timestamp >= cutoff_date)
        .group_by(AuditLog.action_type)
    )
    result = await db.execute(actions_query)
    actions_stats = {row[0]: row[1] for row in result.all()}
    
    # Кількість по типах сутностей
    entities_query = (
        select(AuditLog.entity_type, func.count(AuditLog.id))
        .where(AuditLog.timestamp >= cutoff_date)
        .group_by(AuditLog.entity_type)
    )
    result = await db.execute(entities_query)
    entities_stats = {row[0]: row[1] for row in result.all()}
    
    return {
        "period_days": days,
        "total_logs": total_logs,
        "actions": actions_stats,
        "entities": entities_stats
    }

