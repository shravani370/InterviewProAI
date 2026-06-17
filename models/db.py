"""
Database models using SQLAlchemy ORM
Replaces raw SQLite queries with type-safe models
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Index

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# ═══════════════════════════════════════════════════════════════════════════
# USER MODEL
# ═══════════════════════════════════════════════════════════════════════════

class User(db.Model):
    """User account information"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255))  # hashed password
    auth_type = db.Column(db.String(50), default='email')  # 'email' or 'google'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    screening_results = db.relationship('ScreeningResult', back_populates='user', cascade='all, delete-orphan')
    saved_jobs = db.relationship('SavedJob', back_populates='user', cascade='all, delete-orphan')
    cover_letters = db.relationship('CoverLetter', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<User {self.email}>"


# ═══════════════════════════════════════════════════════════════════════════
# SCREENING_RESULTS MODEL
# ═══════════════════════════════════════════════════════════════════════════

class ScreeningResult(db.Model):
    """Results from screening tests (MCQ + Code)"""
    __tablename__ = 'screening_results'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)  # denormalized for queries
    role = db.Column(db.String(255))
    mcq_score = db.Column(db.Integer)
    code_score = db.Column(db.Integer)
    passed = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', back_populates='screening_results')
    
    __table_args__ = (
        Index('idx_user_role_created', 'user_id', 'role', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ScreeningResult {self.role} - score: {self.mcq_score}/{self.code_score}>"


# ═══════════════════════════════════════════════════════════════════════════
# SAVED_JOBS MODEL
# ═══════════════════════════════════════════════════════════════════════════

class SavedJob(db.Model):
    """Saved job listings for user"""
    __tablename__ = 'saved_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)  # denormalized
    job_id = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255))
    company = db.Column(db.String(255))
    location = db.Column(db.String(255))
    url = db.Column(db.Text)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', back_populates='saved_jobs')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'job_id', name='unique_user_job'),
        Index('idx_user_saved_jobs', 'user_id', 'saved_at'),
    )
    
    def __repr__(self):
        return f"<SavedJob {self.title} at {self.company}>"


# ═══════════════════════════════════════════════════════════════════════════
# COVER_LETTERS MODEL
# ═══════════════════════════════════════════════════════════════════════════

class CoverLetter(db.Model):
    """Generated cover letters"""
    __tablename__ = 'cover_letters'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)  # denormalized
    name = db.Column(db.String(255))
    role = db.Column(db.String(255))
    company = db.Column(db.String(255))
    job_desc = db.Column(db.Text)
    resume_text = db.Column(db.Text)
    letter = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', back_populates='cover_letters')
    
    __table_args__ = (
        Index('idx_user_company_created', 'user_id', 'company', 'created_at'),
    )
    
    def __repr__(self):
        return f"<CoverLetter for {self.role} at {self.company}>"


# ═══════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════

def init_db(app):
    """Initialize database (run migrations instead in production)"""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created/verified")


def reset_db(app):
    """⚠️ DANGER: Drop all tables and recreate (development only)"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ Database reset complete")
