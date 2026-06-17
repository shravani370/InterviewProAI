#!/usr/bin/env python3
"""
Setup script for Interview-ProAI
Initializes database and runs migrations
"""
import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command and report status"""
    print(f"\n{'='*60}")
    print(f"📦 {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        sys.exit(1)
    print(f"✅ Success: {description}")

def main():
    """Main setup flow"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         Interview-ProAI Setup Wizard                      ║
    ║      PostgreSQL + SQLAlchemy + Alembic                   ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Check if .env exists
    if not Path(".env").exists():
        if Path(".env.example").exists():
            print("\n📋 Creating .env from .env.example...")
            run_command("cp .env.example .env", "Copy .env.example to .env")
            print("\n⚠️  Please edit .env with your actual credentials!")
            print("   Then re-run this script.")
            sys.exit(0)
        else:
            print("❌ .env.example not found!")
            sys.exit(1)
    
    # Install dependencies
    run_command("pip install -r requirements.txt", "Install Python dependencies")
    
    # Create database tables
    run_command(
        "python -c \"from app import db, app; app.app_context().push(); db.create_all(); print('✅ Tables created')\"",
        "Initialize database tables"
    )
    
    # Initialize Alembic
    if not Path("alembic/versions").exists():
        print("\n🔄 Alembic not initialized, skipping migration generation...")
    else:
        # Generate initial migration
        run_command(
            "alembic revision --autogenerate -m 'Initial schema from models'",
            "Generate initial Alembic migration"
        )
        
        # Run migrations
        run_command("alembic upgrade head", "Apply database migrations")
    
    print(f"\n{'='*60}")
    print("✅ SETUP COMPLETE!")
    print(f"{'='*60}\n")
    print("""
    Next steps:
    
    1. Start development server:
       python app.py
    
    2. Visit: http://localhost:5000
    
    3. (Optional) Reset database:
       python -c "from app import db, app; app.app_context().push(); db.drop_all(); db.create_all()"
    
    4. (Optional) View database migrations:
       alembic history
       alembic current
    
    Database URLs:
    - PostgreSQL: Check DATABASE_URL in .env
    - Redis: Check REDIS_URL in .env (optional)
    
    Documentation:
    - Database: DATABASE_MIGRATION.md
    - Models: models/db.py
    """)

if __name__ == "__main__":
    main()
