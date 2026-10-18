"""Initial RailConnect schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-18
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401 - register ORM metadata

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the schema from SQLAlchemy metadata."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop all application tables for this revision."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
