import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import HTTPException

from app.core.database import SessionLocal
from app.models import Belt, Student
from app.services.student_service import StudentService


def import_students_from_excel(file_path: str, organization_id: str = None, dojo_id: str = None):
    """Import students from Excel/CSV spreadsheet.

    Expected columns:
    - Nome (required)
    - Email (optional)
    - Telefone (optional)
    - Data_Nascimento (optional, format: DD/MM/YYYY)
    - Categoria (optional, default: 'adult' - values: 'adult', 'child')
    - Faixa (optional, default will be assigned)
    - Matricula (optional, auto-generated if not provided)
    - PIN (optional, default: '1234')
    - Contratante (optional)
    - CPF_Contratante (optional)
    - Rua (optional)
    - Bairro (optional)
    - Cidade (optional)
    - CEP (optional)
    - Aulas_Semana (optional, default: 2)
    - Dias_Aula (optional, ex: 'Seg, Qua, Sex')

    Args:
        file_path: Path to Excel or CSV file
        organization_id: Organization ID (optional for MVP)
        dojo_id: Dojo ID (optional for MVP)
    """
    print(f"Importing students from: {file_path}")

    # Read file
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    print(f"Found {len(df)} records to import")

    db = SessionLocal()

    try:
        # Get default belt (Branca for adults, Branca for children)
        default_belt_adult = db.query(Belt).filter(
            Belt.name == "Branca",
            Belt.category == "adult"
        ).first()

        default_belt_child = db.query(Belt).filter(
            Belt.name == "Branca",
            Belt.category == "child"
        ).first()

        imported = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Required field
                full_name = str(row.get('Nome', '')).strip()
                if not full_name:
                    errors.append(f"Row {index + 2}: Missing name")
                    continue

                # Optional fields
                email = str(row.get('Email', '')).strip() if pd.notna(row.get('Email')) else None
                phone = str(row.get('Telefone', '')).strip() if pd.notna(row.get('Telefone')) else None

                # Birth date
                birth_date = None
                if pd.notna(row.get('Data_Nascimento')):
                    try:
                        date_str = str(row['Data_Nascimento']).strip()
                        birth_date = datetime.strptime(date_str, '%d/%m/%Y')
                    except ValueError:
                        errors.append(f"Row {index + 2}: Invalid date format for {full_name}")

                # Category
                category = 'adult'
                if pd.notna(row.get('Categoria')):
                    cat = str(row['Categoria']).strip().lower()
                    if cat in ['child', 'crianca', 'criança', 'infantil']:
                        category = 'child'

                # Belt
                current_belt_id = None
                if pd.notna(row.get('Faixa')):
                    belt_name = str(row['Faixa']).strip()
                    belt = db.query(Belt).filter(
                        Belt.name.ilike(f"%{belt_name}%"),
                        Belt.category == category
                    ).first()
                    if belt:
                        current_belt_id = belt.id

                if not current_belt_id:
                    current_belt_id = default_belt_child.id if category == 'child' else default_belt_adult.id

                # PIN
                pin = str(row.get('PIN', '1234')).strip()
                if len(pin) != 4 or not pin.isdigit():
                    pin = '1234'

                # Contractor info
                contract_name = str(row.get('Contratante', '')).strip() if pd.notna(row.get('Contratante')) else None
                contract_cpf = str(row.get('CPF_Contratante', '')).strip() if pd.notna(row.get('CPF_Contratante')) else None

                # Address
                address_street = str(row.get('Rua', '')).strip() if pd.notna(row.get('Rua')) else None
                address_neighborhood = str(row.get('Bairro', '')).strip() if pd.notna(row.get('Bairro')) else None
                address_city = str(row.get('Cidade', '')).strip() if pd.notna(row.get('Cidade')) else None
                address_zip = str(row.get('CEP', '')).strip() if pd.notna(row.get('CEP')) else None

                # Schedule
                classes_per_week = 2
                if pd.notna(row.get('Aulas_Semana')):
                    try:
                        classes_per_week = int(row['Aulas_Semana'])
                    except (ValueError, TypeError):
                        pass

                class_days = str(row.get('Dias_Aula', '')).strip() if pd.notna(row.get('Dias_Aula')) else None

                from app.schemas import StudentCreate

                registration_number = None
                if pd.notna(row.get('Matricula')):
                    matricula = str(row['Matricula']).strip()
                    if matricula:
                        existing_reg = db.query(Student).filter(
                            Student.registration_number == matricula
                        ).first()
                        if existing_reg:
                            errors.append(
                                f"Row {index + 2}: Matricula '{matricula}' for {full_name} "
                                f"already in use by {existing_reg.full_name} (matricula: {matricula}). "
                                f"Skipping. Please resolve manually."
                            )
                            continue
                        registration_number = matricula

                student_data = StudentCreate(
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    birth_date=birth_date,
                    category=category,
                    current_belt_id=current_belt_id,
                    dojo_id=dojo_id,
                    pin=pin,
                    registration_number=registration_number,
                    contract_name=contract_name,
                    contract_cpf=contract_cpf,
                    address_street=address_street,
                    address_neighborhood=address_neighborhood,
                    address_city=address_city,
                    address_zip=address_zip,
                    classes_per_week=classes_per_week,
                    class_days=class_days,
                )

                # Check if student already exists by name
                existing = db.query(Student).filter(
                    Student.full_name.ilike(f"%{full_name}%")
                ).first()

                if existing:
                    errors.append(f"Row {index + 2}: Student {full_name} already exists")
                    continue

                try:
                    _ = StudentService.create_student(db, student_data)
                except HTTPException as e:
                    if e.status_code == 409:
                        errors.append(
                            f"Row {index + 2}: Matricula '{registration_number}' for {full_name} "
                            f"is already in use (conflict detected during creation). Skipping."
                        )
                    else:
                        errors.append(f"Row {index + 2}: Error creating {full_name}: {str(e.detail)}")
                    continue
                imported += 1

                if imported % 10 == 0:
                    print(f"Imported {imported} students...")

            except Exception as e:
                errors.append(f"Row {index + 2}: Error importing {full_name}: {str(e)}")

        print("\nImport complete!")
        print(f"Successfully imported: {imported} students")
        print(f"Errors: {len(errors)}")

        if errors:
            print("\nErrors encountered:")
            for error in errors[:20]:  # Show first 20 errors
                print(f"  - {error}")
            if len(errors) > 20:
                print(f"  ... and {len(errors) - 20} more")

        return imported, errors

    finally:
        db.close()


def create_sample_belts(db: SessionLocal):
    """Create default belts if they don't exist."""
    belts = [
        # Adult belts
        {"name": "Branca", "category": "adult", "sort_order": 1},
        {"name": "Amarela", "category": "adult", "sort_order": 2},
        {"name": "Roxa", "category": "adult", "sort_order": 3},
        {"name": "Verde", "category": "adult", "sort_order": 4},
        {"name": "Azul", "category": "adult", "sort_order": 5},
        {"name": "Marrom", "category": "adult", "sort_order": 6},
        {"name": "Shodan", "category": "adult", "sort_order": 7},
        {"name": "Nidan", "category": "adult", "sort_order": 8},
        {"name": "Sandan", "category": "adult", "sort_order": 9},
        {"name": "Godan", "category": "adult", "sort_order": 10},
        # Child belts
        {"name": "Branca", "category": "child", "sort_order": 1},
        {"name": "Branca Ponta Laranja", "category": "child", "sort_order": 2},
        {"name": "Laranja", "category": "child", "sort_order": 3},
        {"name": "Laranja Ponta Cinza", "category": "child", "sort_order": 4},
        {"name": "Cinza", "category": "child", "sort_order": 5},
        {"name": "Cinza Ponta Vermelha", "category": "child", "sort_order": 6},
        {"name": "Vermelha", "category": "child", "sort_order": 7},
        {"name": "Vermelha Ponta Amarela", "category": "child", "sort_order": 8},
    ]

    created = 0
    for belt_data in belts:
        existing = db.query(Belt).filter(
            Belt.name == belt_data["name"],
            Belt.category == belt_data["category"]
        ).first()

        if not existing:
            belt = Belt(**belt_data)
            db.add(belt)
            created += 1

    db.commit()
    print(f"Created {created} default belts")


def main():
    parser = argparse.ArgumentParser(description='Import students from Excel/CSV file')
    parser.add_argument('file', help='Path to Excel or CSV file')
    parser.add_argument('--org-id', help='Organization ID (optional)', default=None)
    parser.add_argument('--dojo-id', help='Dojo ID (optional)', default=None)
    parser.add_argument('--create-belts', action='store_true', help='Create default belts if not exists')

    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.create_belts:
            create_sample_belts(db)

        # Check if belts exist
        belt_count = db.query(Belt).count()
        if belt_count == 0:
            print("No belts found. Creating default belts...")
            create_sample_belts(db)
    finally:
        db.close()

    imported, errors = import_students_from_excel(
        args.file,
        organization_id=args.org_id,
        dojo_id=args.dojo_id
    )

    print(f"\nTotal imported: {imported}")
    if errors:
        print(f"Total errors: {len(errors)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
