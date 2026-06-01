import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models import Base, User, Belt, EventType, Organization


def seed_database(db: Session):
    """Seed database with initial data."""
    
    print("Checking database state...")
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Check if data already exists
    existing_users = db.query(User).count()
    if existing_users > 0:
        print(f"Database already seeded ({existing_users} users found). Skipping.")
        return
    
    print("Seeding database...")
    
    # Create default organization
    print("Creating default organization...")
    org = Organization(
        name="Minha Organização",
        description="Organização principal do dojo"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    print(f"  Created: {org.name}")

    print("Creating default dojos...")
    from app.models import Dojo
    dojos = [
        {"organization_id": org.id, "code": 1, "name": "Dojo Sede", "address": "Endereço da sede"},
        {"organization_id": org.id, "code": 2, "name": "Dojo Filial 1", "address": "Endereço da filial 1"},
        {"organization_id": org.id, "code": 3, "name": "Dojo Filial 2", "address": "Endereço da filial 2"},
    ]
    for dojo_data in dojos:
        dojo = Dojo(**dojo_data)
        db.add(dojo)
    db.commit()
    print(f"  Created: {len(dojos)} dojos")

    # Create admin user
    print("Creating admin user...")
    admin_password = "admin123"[:72]  # bcrypt max 72 bytes
    admin = User(
        email="admin@dojo.com",
        password_hash=get_password_hash(admin_password),
        full_name="Administrador",
        role="admin",
        is_active=True,
        organization_id=org.id
    )
    db.add(admin)
    
    # Create sample instructor
    instructor_password = "instruct123"[:72]  # bcrypt max 72 bytes
    instructor = User(
        email="instructor@dojo.com",
        password_hash=get_password_hash(instructor_password),
        full_name="Instrutor Exemplo",
        role="instructor",
        is_active=True,
        organization_id=org.id
    )
    db.add(instructor)
    db.commit()
    print("  Created: admin@dojo.com / admin123 (admin)")
    print("  Created: instructor@dojo.com / instruct123 (instructor)")
    
    # Create belts
    print("Creating belts...")
    belts = [
        # Adult belts
        {"name": "Branca", "category": "adult", "sort_order": 1, "organization_id": org.id},
        {"name": "Amarela", "category": "adult", "sort_order": 2, "organization_id": org.id},
        {"name": "Roxa", "category": "adult", "sort_order": 3, "organization_id": org.id},
        {"name": "Verde", "category": "adult", "sort_order": 4, "organization_id": org.id},
        {"name": "Azul", "category": "adult", "sort_order": 5, "organization_id": org.id},
        {"name": "Marrom", "category": "adult", "sort_order": 6, "organization_id": org.id},
        {"name": "Preta", "category": "adult", "sort_order": 7, "organization_id": org.id},
        {"name": "Shodan", "category": "adult", "sort_order": 8, "organization_id": org.id},
        {"name": "Nidan", "category": "adult", "sort_order": 9, "organization_id": org.id},
        {"name": "Sandan", "category": "adult", "sort_order": 10, "organization_id": org.id},
        {"name": "Godan", "category": "adult", "sort_order": 11, "organization_id": org.id},
        # Child belts
        {"name": "Branca", "category": "child", "sort_order": 1, "organization_id": org.id},
        {"name": "Branca Ponta Laranja", "category": "child", "sort_order": 2, "organization_id": org.id},
        {"name": "Laranja", "category": "child", "sort_order": 3, "organization_id": org.id},
        {"name": "Laranja Ponta Cinza", "category": "child", "sort_order": 4, "organization_id": org.id},
        {"name": "Cinza", "category": "child", "sort_order": 5, "organization_id": org.id},
        {"name": "Cinza Ponta Vermelha", "category": "child", "sort_order": 6, "organization_id": org.id},
        {"name": "Vermelha", "category": "child", "sort_order": 7, "organization_id": org.id},
        {"name": "Vermelha Ponta Amarela", "category": "child", "sort_order": 8, "organization_id": org.id},
    ]
    
    for belt_data in belts:
        belt = Belt(**belt_data)
        db.add(belt)
    
    db.commit()
    print(f"  Created: {len(belts)} belts")
    
    # Create event types
    print("Creating event types...")
    event_types = [
        {"name": "Aula Regular", "color": "#3B82F6", "counts_for_belt": True},
        {"name": "Treino de Graduados", "color": "#8B5CF6", "counts_for_belt": True},
        {"name": "Limpeza do Dojo", "color": "#10B981", "counts_for_belt": False},
        {"name": "Evento Especial", "color": "#F59E0B", "counts_for_belt": False},
        {"name": "Exame de Faixa", "color": "#EF4444", "counts_for_belt": False},
    ]
    
    for event_type_data in event_types:
        event_type = EventType(**event_type_data)
        db.add(event_type)
    
    db.commit()
    print(f"  Created: {len(event_types)} event types")
    
    print("Database seeded successfully!")
    print("\nLogin credentials:")
    print("  Admin: admin@dojo.com / admin123")
    print("  Instructor: instructor@dojo.com / instruct123")


def main():
    print("Dojo Admin - Database Seeder")
    print("=" * 30)
    
    db = SessionLocal()
    try:
        seed_database(db)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()
    
    print("Done!")


if __name__ == "__main__":
    main()
