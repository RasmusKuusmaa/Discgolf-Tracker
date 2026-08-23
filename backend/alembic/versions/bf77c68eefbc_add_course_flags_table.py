"""add course flags table

Revision ID: bf77c68eefbc
Revises: 2745f5fd6c00
Create Date: 2026-08-23 09:16:24.335342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf77c68eefbc'
down_revision: Union[str, Sequence[str], None] = '2745f5fd6c00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('course_flags',
    sa.Column('course_id', sa.UUID(), nullable=False),
    sa.Column('reported_by_id', sa.UUID(), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['reported_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_flags_course_id'), 'course_flags', ['course_id'], unique=False)
    op.create_index(op.f('ix_course_flags_reported_by_id'), 'course_flags', ['reported_by_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_course_flags_reported_by_id'), table_name='course_flags')
    op.drop_index(op.f('ix_course_flags_course_id'), table_name='course_flags')
    op.drop_table('course_flags')
