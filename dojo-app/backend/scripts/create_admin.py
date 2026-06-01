import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.services.auth_service import UserService
from app.schemas import UserCreate


def create_admin_user(email: str, password: str, full_name: str):
    """Create the first admin user."""
    db = SessionLocal()
    
    try:
        # Check if any users exist
        existing = UserService.get_user_by_email(db, email)
        if existing:
            print(f"User {email} already exists!")
            print(f"Role: {existing.role}")
            return False
        
        user_data = UserCreate(
            email=email,
            password=password,
            full_name=full_name,
            role="admin",
            is_active=True
        )
        
        user = UserService.create_user(db, user_data)
        print(f"Admin user created successfully!")
        print(f"  Email: {user.email}")
        print(f"  Name: {user.full_name}")
        print(f"  Role: {user.role}")
        return True
        
    except Exception as e:
        print(f"Error creating admin: {e}")
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Create admin user for Dojo Admin')
    parser.add_argument('--email', default='admin@dojo.com', help='Admin email')
    parser.add_argument('--password', default='admin123', help='Admin password')
    parser.add_argument('--name', default='Administrador', help='Admin full name')
    
    args = parser.parse_args()
    
    print("Creating admin user...")
    success = create_admin_user(args.email, args.password, args.name)
    
    if success:
        print("\nYou can now login with:")
        print(f"  Email: {args.email}")
        print(f"  Password: {args.password}")
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
