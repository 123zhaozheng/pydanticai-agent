"""
Alembic migration script for creating tools and skills tables.

Revision ID: 001_add_tools_skills
Create Date: 2025-12-23

Run this migration with:
    alembic upgrade head

Or if not using Alembic, run the SQL directly in your database.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '001_add_tools_skills'
down_revision = None  # Replace with your last migration ID
branch_labels = None
depends_on = None


def upgrade():
    """Create all tools and skills related tables."""
    
    # 1. Create mcp_tools table
    op.create_table(
        'mcp_tools',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, comment='Tool identifier'),
        sa.Column('description', sa.Text(), nullable=True, comment='Human-readable description'),
        sa.Column('transport_type', sa.Enum('http', 'sse', 'stdio', name='transporttype'), 
                  nullable=False, comment='MCP transport protocol'),
        sa.Column('url', sa.String(length=500), nullable=True, comment='Endpoint URL for HTTP/SSE'),
        sa.Column('command', sa.Text(), nullable=True, comment='Command for stdio transport'),
        sa.Column('input_schema', sa.JSON(), nullable=False, comment='JSON Schema for tool parameters'),
        sa.Column('metadata', sa.JSON(), nullable=True, comment='Additional metadata'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=True, default=False),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True, default=120),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='MCP Tool Registry'
    )
    op.create_index('ix_mcp_tools_id', 'mcp_tools', ['id'])
    op.create_index('ix_mcp_tools_name', 'mcp_tools', ['name'], unique=True)
    op.create_index('ix_mcp_tools_transport_type', 'mcp_tools', ['transport_type'])
    op.create_index('ix_mcp_tools_is_active', 'mcp_tools', ['is_active'])
    
    # 2. Create skills table
    op.create_table(
        'skills',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, comment='Skill identifier'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('path', sa.String(length=500), nullable=False, comment='Path to SKILL.md directory'),
        sa.Column('version', sa.String(length=50), nullable=True, default='1.0.0'),
        sa.Column('author', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True, comment='Array of tags'),
        sa.Column('resources', sa.JSON(), nullable=True, comment='List of resource files'),
        sa.Column('frontmatter', sa.JSON(), nullable=True, comment='YAML frontmatter from SKILL.md'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='Skill Package Registry'
    )
    op.create_index('ix_skills_id', 'skills', ['id'])
    op.create_index('ix_skills_name', 'skills', ['name'], unique=True)
    op.create_index('ix_skills_is_active', 'skills', ['is_active'])
    
    # 3. Create role_tool_permissions table
    op.create_table(
        'role_tool_permissions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('tool_id', sa.BigInteger(), nullable=False),
        sa.Column('can_use', sa.Boolean(), nullable=True, default=True),
        sa.Column('can_configure', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tool_id'], ['mcp_tools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Role-Tool Permission Mapping'
    )
    op.create_index('ix_role_tool_permissions_id', 'role_tool_permissions', ['id'])
    op.create_index('ix_role_tool_permissions_role_id', 'role_tool_permissions', ['role_id'])
    op.create_index('ix_role_tool_permissions_tool_id', 'role_tool_permissions', ['tool_id'])
    op.create_unique_constraint('uq_role_tool', 'role_tool_permissions', ['role_id', 'tool_id'])
    
    # 4. Create role_skill_permissions table
    op.create_table(
        'role_skill_permissions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('skill_id', sa.BigInteger(), nullable=False),
        sa.Column('can_use', sa.Boolean(), nullable=True, default=True),
        sa.Column('can_manage', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Role-Skill Permission Mapping'
    )
    op.create_index('ix_role_skill_permissions_id', 'role_skill_permissions', ['id'])
    op.create_index('ix_role_skill_permissions_role_id', 'role_skill_permissions', ['role_id'])
    op.create_index('ix_role_skill_permissions_skill_id', 'role_skill_permissions', ['skill_id'])
    op.create_unique_constraint('uq_role_skill', 'role_skill_permissions', ['role_id', 'skill_id'])
    
    # 5. Create department_tool_permissions table
    op.create_table(
        'department_tool_permissions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('tool_id', sa.BigInteger(), nullable=False),
        sa.Column('is_allowed', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tool_id'], ['mcp_tools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Department-level Tool Access Control'
    )
    op.create_index('ix_department_tool_permissions_id', 'department_tool_permissions', ['id'])
    op.create_index('ix_department_tool_permissions_department_id', 'department_tool_permissions', ['department_id'])
    op.create_index('ix_department_tool_permissions_tool_id', 'department_tool_permissions', ['tool_id'])
    op.create_unique_constraint('uq_dept_tool', 'department_tool_permissions', ['department_id', 'tool_id'])
    
    # 6. Create department_skill_permissions table
    op.create_table(
        'department_skill_permissions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('skill_id', sa.BigInteger(), nullable=False),
        sa.Column('is_allowed', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Department-level Skill Access Control'
    )
    op.create_index('ix_department_skill_permissions_id', 'department_skill_permissions', ['id'])
    op.create_index('ix_department_skill_permissions_department_id', 'department_skill_permissions', ['department_id'])
    op.create_index('ix_department_skill_permissions_skill_id', 'department_skill_permissions', ['skill_id'])
    op.create_unique_constraint('uq_dept_skill', 'department_skill_permissions', ['department_id', 'skill_id'])


def downgrade():
    """Drop all tools and skills related tables."""
    op.drop_table('department_skill_permissions')
    op.drop_table('department_tool_permissions')
    op.drop_table('role_skill_permissions')
    op.drop_table('role_tool_permissions')
    op.drop_table('skills')
    op.drop_table('mcp_tools')
