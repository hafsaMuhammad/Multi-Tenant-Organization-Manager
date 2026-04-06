from app.db.session import Base
import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, ForeignKey,
    Index, JSON, String, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship



def utcnow():
    return datetime.now(timezone.utc)



#user model

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # default=utcnow runs in Python before insert
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now())
    memberships: Mapped[list["Membership"]] = relationship(
        "Membership", back_populates="user", cascade="all, delete-orphan")
    items: Mapped[list["Item"]] = relationship(
        "Item", back_populates="created_by_user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="actor")
    
    
#Role 

class RoleEnum(str, enum.Enum):
    admin = "admin"
    member = "member"


# Organization model

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    memberships: Mapped[list["Membership"]] = relationship(
        "Membership", back_populates="organization", cascade="all, delete-orphan"
    )
    items: Mapped[list["Item"]] = relationship(
        "Item", back_populates="organization", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="organization", cascade="all, delete-orphan"
    )





# Mermbership, it is the through table for the M to N relationship between user and org.

class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, name="roleenum"), nullable=False, default=RoleEnum.member
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="memberships")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
    #the user can only have one role per org
    __table_args__ = (
        Index("uq_membership_user_org", "user_id", "org_id", unique=True),
    )
    

#actions that fill the audit logs

class AuditActionEnum(str, enum.Enum):
    org_created = "org_created"
    user_invited = "user_invited"
    item_created = "item_created"
    item_viewed = "item_viewed"
    user_registered = "user_registered"
    
    
    
class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="items")
    created_by_user: Mapped["User"] = relationship("User", back_populates="items")
    
    
    
    
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[AuditActionEnum] = mapped_column(
        Enum(AuditActionEnum, name="auditactionenum"), nullable=False
    )
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), index=True
    )

    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="audit_logs")
    actor: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
    __table_args__ = (
        Index("ix_audit_logs_org_created", "org_id", "created_at"),
    )