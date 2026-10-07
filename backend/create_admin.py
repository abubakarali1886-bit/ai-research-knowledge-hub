"""
Create admin user script
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def create_admin():
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            print("✅ Admin user already exists")
            print(f"   Username: {admin.username}")
            print(f"   Role: {admin.role}")
            return
        
        # Create admin - simple password
        password = "admin123"
        password_hash = get_password_hash(password)
        
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=password_hash,
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print("=" * 50)
        print("✅ ADMIN USER CREATED SUCCESSFULLY!")
        print("=" * 50)
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"   Role: ADMIN")
        print(f"   Email: admin@example.com")
        print("=" * 50)
        print("   Please change password after first login!")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

def create_test_researcher():
    """Create a test researcher user"""
    db = SessionLocal()
    try:
        # Check if researcher exists
        researcher = db.query(User).filter(User.username == "researcher").first()
        if researcher:
            print("✅ Researcher user already exists")
            return
        
        password = "researcher123"
        password_hash = get_password_hash(password)
        
        researcher_user = User(
            username="researcher",
            email="researcher@example.com",
            password_hash=password_hash,
            full_name="Test Researcher",
            role=UserRole.RESEARCHER,
            is_active=True,
            is_verified=True
        )
        
        db.add(researcher_user)
        db.commit()
        
        print("=" * 50)
        print("✅ RESEARCHER USER CREATED SUCCESSFULLY!")
        print("=" * 50)
        print(f"   Username: researcher")
        print(f"   Password: researcher123")
        print(f"   Role: RESEARCHER")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error creating researcher: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("\n🔐 CREATING USERS...\n")
    create_admin()
    print()
    create_test_researcher()
    print("\n✅ Done!\n")