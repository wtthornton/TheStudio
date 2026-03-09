"""Role-Based Access Control (RBAC) for Admin API.

Story 4.8: RBAC — Role Definitions, API Enforcement.
Architecture reference: thestudioarc/22-architecture-guardrails.md

Provides:
- Role and Permission definitions
- User role database model
- RBAC service for permission checking
- FastAPI dependencies for role enforcement
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.connection import get_session

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class Role(StrEnum):
    """User roles for Admin UI access control.

    Roles follow principle of least privilege:
    - ADMIN: Full access to all admin operations
    - OPERATOR: View access + limited operational actions
    - VIEWER: Read-only access to dashboards and status
    """

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(StrEnum):
    """Permissions for Admin UI operations.

    Permissions are mapped to roles via ROLE_PERMISSIONS.
    """

    # Read permissions (Viewer+)
    VIEW_HEALTH = "view_health"
    VIEW_REPOS = "view_repos"
    VIEW_WORKFLOWS = "view_workflows"
    VIEW_METRICS = "view_metrics"

    # Operational permissions (Operator+)
    PAUSE_REPO = "pause_repo"
    RESUME_REPO = "resume_repo"
    RERUN_VERIFICATION = "rerun_verification"
    SEND_TO_AGENT = "send_to_agent"
    ESCALATE_WORKFLOW = "escalate_workflow"

    # Administrative permissions (Admin only)
    REGISTER_REPO = "register_repo"
    UPDATE_REPO_PROFILE = "update_repo_profile"
    CHANGE_REPO_TIER = "change_repo_tier"
    TOGGLE_WRITES = "toggle_writes"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT = "view_audit"
    MANAGE_SETTINGS = "manage_settings"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset({
        Permission.VIEW_HEALTH,
        Permission.VIEW_REPOS,
        Permission.VIEW_WORKFLOWS,
        Permission.VIEW_METRICS,
    }),
    Role.OPERATOR: frozenset({
        # Inherits viewer permissions
        Permission.VIEW_HEALTH,
        Permission.VIEW_REPOS,
        Permission.VIEW_WORKFLOWS,
        Permission.VIEW_METRICS,
        # Operational permissions
        Permission.PAUSE_REPO,
        Permission.RESUME_REPO,
        Permission.RERUN_VERIFICATION,
        Permission.SEND_TO_AGENT,
        Permission.ESCALATE_WORKFLOW,
    }),
    Role.ADMIN: frozenset({
        # All permissions
        Permission.VIEW_HEALTH,
        Permission.VIEW_REPOS,
        Permission.VIEW_WORKFLOWS,
        Permission.VIEW_METRICS,
        Permission.PAUSE_REPO,
        Permission.RESUME_REPO,
        Permission.RERUN_VERIFICATION,
        Permission.SEND_TO_AGENT,
        Permission.ESCALATE_WORKFLOW,
        Permission.REGISTER_REPO,
        Permission.UPDATE_REPO_PROFILE,
        Permission.CHANGE_REPO_TIER,
        Permission.TOGGLE_WRITES,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT,
        Permission.MANAGE_SETTINGS,
    }),
}


class UserRoleRow(Base):
    """SQLAlchemy ORM model for the user_roles table."""

    __tablename__ = "user_roles"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="user_role", create_constraint=True),
        nullable=False,
        default=Role.VIEWER,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = ({"comment": "User role assignments for Admin UI RBAC"},)


class UserRoleCreate(BaseModel):
    """Input for creating a user role assignment."""

    user_id: str = Field(..., min_length=1, max_length=255)
    role: Role = Role.VIEWER


class UserRoleRead(BaseModel):
    """Output for reading a user role assignment."""

    model_config = {"from_attributes": True}

    id: UUID
    user_id: str
    role: Role
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None


class UserRoleUpdate(BaseModel):
    """Input for updating a user role assignment."""

    role: Role


class UserRoleNotFoundError(Exception):
    """Raised when user role is not found."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(f"User role for {user_id} not found")


class UserRoleDuplicateError(Exception):
    """Raised when user role already exists."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(f"User role for {user_id} already exists")


class PermissionDeniedError(Exception):
    """Raised when user lacks required permission."""

    def __init__(self, user_id: str, permission: Permission) -> None:
        self.user_id = user_id
        self.permission = permission
        super().__init__(f"User {user_id} lacks permission {permission.value}")


class RBACService:
    """Service for RBAC operations.

    Usage:
        service = RBACService()
        role = await service.get_user_role(session, "user@example.com")
        if service.has_permission(role, Permission.REGISTER_REPO):
            ...
    """

    async def get_user_role(
        self, session: AsyncSession, user_id: str
    ) -> Role | None:
        """Get role for a user.

        Args:
            session: Database session.
            user_id: User identifier (e.g., email or OAuth ID).

        Returns:
            Role if user has assignment, None otherwise.
        """
        stmt = select(UserRoleRow).where(UserRoleRow.user_id == user_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return row.role if row else None

    async def get_user_role_record(
        self, session: AsyncSession, user_id: str
    ) -> UserRoleRow | None:
        """Get full role record for a user.

        Args:
            session: Database session.
            user_id: User identifier.

        Returns:
            UserRoleRow if found, None otherwise.
        """
        stmt = select(UserRoleRow).where(UserRoleRow.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user_role(
        self,
        session: AsyncSession,
        data: UserRoleCreate,
        created_by: str | None = None,
    ) -> UserRoleRow:
        """Create a user role assignment.

        Args:
            session: Database session.
            data: User role data.
            created_by: User who created this assignment.

        Returns:
            Created UserRoleRow.

        Raises:
            UserRoleDuplicateError: If user already has a role.
        """
        existing = await self.get_user_role_record(session, data.user_id)
        if existing:
            raise UserRoleDuplicateError(data.user_id)

        row = UserRoleRow(
            user_id=data.user_id,
            role=data.role,
            created_by=created_by,
        )
        session.add(row)
        await session.flush()
        return row

    async def update_user_role(
        self,
        session: AsyncSession,
        user_id: str,
        data: UserRoleUpdate,
    ) -> UserRoleRow:
        """Update a user role assignment.

        Args:
            session: Database session.
            user_id: User identifier.
            data: Updated role data.

        Returns:
            Updated UserRoleRow.

        Raises:
            UserRoleNotFoundError: If user role not found.
        """
        row = await self.get_user_role_record(session, user_id)
        if not row:
            raise UserRoleNotFoundError(user_id)

        row.role = data.role
        await session.flush()
        return row

    async def delete_user_role(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> None:
        """Delete a user role assignment.

        Args:
            session: Database session.
            user_id: User identifier.

        Raises:
            UserRoleNotFoundError: If user role not found.
        """
        row = await self.get_user_role_record(session, user_id)
        if not row:
            raise UserRoleNotFoundError(user_id)

        await session.delete(row)
        await session.flush()

    async def list_user_roles(
        self,
        session: AsyncSession,
    ) -> list[UserRoleRow]:
        """List all user role assignments.

        Args:
            session: Database session.

        Returns:
            List of UserRoleRow records.
        """
        stmt = select(UserRoleRow).order_by(UserRoleRow.user_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def has_permission(self, role: Role | None, permission: Permission) -> bool:
        """Check if a role has a specific permission.

        Args:
            role: User's role (None if no role assigned).
            permission: Permission to check.

        Returns:
            True if role has permission, False otherwise.
        """
        if role is None:
            return False
        return permission in ROLE_PERMISSIONS.get(role, frozenset())

    def check_permission(
        self, role: Role | None, permission: Permission, user_id: str
    ) -> None:
        """Check permission and raise if denied.

        Args:
            role: User's role.
            permission: Required permission.
            user_id: User identifier (for error message).

        Raises:
            PermissionDeniedError: If permission is denied.
        """
        if not self.has_permission(role, permission):
            raise PermissionDeniedError(user_id, permission)


_rbac_service: RBACService | None = None


def get_rbac_service() -> RBACService:
    """Get or create RBAC service instance."""
    global _rbac_service
    if _rbac_service is None:
        _rbac_service = RBACService()
    return _rbac_service


def set_rbac_service(service: RBACService | None) -> None:
    """Set RBAC service (for testing)."""
    global _rbac_service
    _rbac_service = service


def get_current_user_id(request: Request) -> str:
    """Extract current user ID from request.

    In production, this would extract from JWT token or OAuth session.
    For now, uses X-User-ID header for testing.

    Args:
        request: FastAPI request.

    Returns:
        User ID string.

    Raises:
        HTTPException 401: If no user ID found.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user_id


async def get_current_user_role(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Role | None:
    """Get current user's role from database.

    Args:
        user_id: Current user ID.
        session: Database session.

    Returns:
        User's role or None if no role assigned.
    """
    service = get_rbac_service()
    return await service.get_user_role(session, user_id)


def require_permission(permission: Permission):
    """Create a dependency that requires a specific permission.

    Usage:
        @router.post("/repos", dependencies=[Depends(require_permission(Permission.REGISTER_REPO))])
        async def register_repo(...):
            ...

    Args:
        permission: Required permission.

    Returns:
        FastAPI dependency function.
    """

    async def permission_checker(
        user_id: Annotated[str, Depends(get_current_user_id)],
        role: Annotated[Role | None, Depends(get_current_user_role)],
    ) -> None:
        service = get_rbac_service()
        if not service.has_permission(role, permission):
            logger.warning(
                "Permission denied: user=%s role=%s permission=%s",
                user_id,
                role.value if role else "none",
                permission.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} requires "
                f"{_get_minimum_role_for_permission(permission).value} role or higher",
            )

    return permission_checker


def _get_minimum_role_for_permission(permission: Permission) -> Role:
    """Get the minimum role required for a permission."""
    for role in [Role.VIEWER, Role.OPERATOR, Role.ADMIN]:
        if permission in ROLE_PERMISSIONS[role]:
            return role
    return Role.ADMIN
