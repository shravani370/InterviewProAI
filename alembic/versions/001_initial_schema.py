"""Initial schema with users, screening_results, saved_jobs, and cover_letters tables

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial database schema"""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=True),
        sa.Column('auth_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create screening_results table
    op.create_table(
        'screening_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=255), nullable=True),
        sa.Column('mcq_score', sa.Integer(), nullable=True),
        sa.Column('code_score', sa.Integer(), nullable=True),
        sa.Column('passed', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_screening_results_created_at'), 'screening_results', ['created_at'], unique=False)
    op.create_index(op.f('ix_screening_results_email'), 'screening_results', ['email'], unique=False)
    op.create_index(op.f('ix_screening_results_user_id'), 'screening_results', ['user_id'], unique=False)
    op.create_index('idx_user_role_created', 'screening_results', ['user_id', 'role', 'created_at'], unique=False)
    
    # Create saved_jobs table
    op.create_table(
        'saved_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('job_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('saved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'job_id', name='unique_user_job')
    )
    op.create_index(op.f('ix_saved_jobs_email'), 'saved_jobs', ['email'], unique=False)
    op.create_index(op.f('ix_saved_jobs_saved_at'), 'saved_jobs', ['saved_at'], unique=False)
    op.create_index(op.f('ix_saved_jobs_user_id'), 'saved_jobs', ['user_id'], unique=False)
    op.create_index('idx_user_saved_jobs', 'saved_jobs', ['user_id', 'saved_at'], unique=False)
    
    # Create cover_letters table
    op.create_table(
        'cover_letters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=255), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('job_desc', sa.Text(), nullable=True),
        sa.Column('resume_text', sa.Text(), nullable=True),
        sa.Column('letter', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cover_letters_created_at'), 'cover_letters', ['created_at'], unique=False)
    op.create_index(op.f('ix_cover_letters_email'), 'cover_letters', ['email'], unique=False)
    op.create_index(op.f('ix_cover_letters_user_id'), 'cover_letters', ['user_id'], unique=False)
    op.create_index('idx_user_company_created', 'cover_letters', ['user_id', 'company', 'created_at'], unique=False)


def downgrade():
    """Drop all tables"""
    
    # Drop indices and tables in reverse order
    op.drop_index('idx_user_company_created', table_name='cover_letters')
    op.drop_index(op.f('ix_cover_letters_user_id'), table_name='cover_letters')
    op.drop_index(op.f('ix_cover_letters_email'), table_name='cover_letters')
    op.drop_index(op.f('ix_cover_letters_created_at'), table_name='cover_letters')
    op.drop_table('cover_letters')
    
    op.drop_index('idx_user_saved_jobs', table_name='saved_jobs')
    op.drop_index(op.f('ix_saved_jobs_user_id'), table_name='saved_jobs')
    op.drop_index(op.f('ix_saved_jobs_saved_at'), table_name='saved_jobs')
    op.drop_index(op.f('ix_saved_jobs_email'), table_name='saved_jobs')
    op.drop_table('saved_jobs')
    
    op.drop_index('idx_user_role_created', table_name='screening_results')
    op.drop_index(op.f('ix_screening_results_user_id'), table_name='screening_results')
    op.drop_index(op.f('ix_screening_results_email'), table_name='screening_results')
    op.drop_index(op.f('ix_screening_results_created_at'), table_name='screening_results')
    op.drop_table('screening_results')
    
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_created_at'), table_name='users')
    op.drop_table('users')
