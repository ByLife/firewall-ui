"""
Audit Log Model
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    """Audit log for tracking user actions"""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User who performed the action
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(50), nullable=True)
    
    # Action details
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, EXECUTE
    resource_type = Column(String(50), nullable=False)  # firewall_rule, route, port_scan, etc.
    resource_id = Column(String(100), nullable=True)
    
    # Details
    description = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)  # Additional JSON data
    
    # Request info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    # Result
    status = Column(String(20), default="success")  # success, failed, error
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=func.now(), index=True)
    
    def __repr__(self):
        return f"<AuditLog {self.action} {self.resource_type} by {self.username}>"
