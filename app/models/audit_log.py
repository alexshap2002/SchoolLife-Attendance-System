"""Audit log model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    """Audit log model for tracking all changes in the system."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        index=True
    )
    
    # Who made the change
    user_type: Mapped[str] = mapped_column(String(50), nullable=False, default='admin')  # 'admin', 'teacher', 'system'
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # What happened
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'CREATE', 'UPDATE', 'DELETE'
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'student', 'teacher', 'club', etc.
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    entity_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # For quick search
    
    # Details
    description: Mapped[str] = mapped_column(Text, nullable=False)  # Human-readable description
    changes_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"before": {...}, "after": {...}}
    
    # Legacy fields (для сумісності)
    actor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Додаткові індекси для швидкого пошуку
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_entity_type_id', 'entity_type', 'entity_id'),
        Index('idx_audit_action_entity', 'action_type', 'entity_type'),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, actor='{self.actor}', "
            f"action='{self.action}', entity='{self.entity}', "
            f"entity_id={self.entity_id}, created_at={self.created_at})>"
        )
