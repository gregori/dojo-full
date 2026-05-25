# Story 02-02: Student Management

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-2-students

## User Story

As an **instructor**, I want to register and manage student profiles with all relevant information, so that I have a complete record of each student's details, belt status, and history.

As a **student**, I want to view my own profile, so that I can see my current belt, enrollment date, and personal information.

## Acceptance Criteria

### AC-1: Create Student

**Given** an instructor is on the student management page  
**When** they fill in the student registration form and submit  
**Then**:
- A new student record is created with all fields
- The student is linked to the instructor's organization (`org_id`)
- If the student has an existing user account, it is linked; otherwise, a user account is created with `student` role
- The student appears in the student list

### AC-2: Student Fields

**Given** a student record  
**When** it is created or updated  
**Then** it must support these fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | VARCHAR(255) | Yes | Full name |
| phone | VARCHAR(20) | Yes | Contact phone |
| email | VARCHAR(255) | No | Email address |
| address | TEXT | No | Full address |
| cpf | VARCHAR(14) | No | Brazilian CPF |
| contractor | VARCHAR(255) | No | Parent/guardian (for minors) |
| medical_certificate | VARCHAR(500) | No | PDF file path/URL |
| previous_grade | VARCHAR(50) | No | Belt grade before joining |
| current_belt_id | UUID | Yes | FK to belts table |
| status | ENUM | Yes | active, inactive, graduated |
| photo | VARCHAR(500) | No | Photo file path/URL |
| emergency_contact | VARCHAR(255) | No | Emergency contact name + phone |
| enrollment_date | DATE | Yes | Date of joining the dojo |
| org_id | UUID | Yes | Organization scope |

### AC-3: View Student List

**Given** an instructor or student is authenticated  
**When** they view the student list  
**Then**:
- Instructors see all students in their organization
- Students see only their own profile
- The list shows name, current belt, status, and enrollment date
- Results are paginated and searchable by name

### AC-4: Update Student

**Given** an instructor views a student's profile  
**When** they edit and save changes  
**Then**:
- All editable fields are updated
- Belt changes are tracked (see Belt System story)
- The update timestamp is recorded

### AC-5: Deactivate Student

**Given** an instructor views a student's profile  
**When** they change the student's status to "inactive"  
**Then**:
- The student is marked as inactive
- The student can no longer mark attendance
- The student's record is preserved (not deleted)
- The student can be reactivated later

### AC-6: Medical Certificate Upload

**Given** an instructor is registering or editing a student  
**When** they upload a medical certificate PDF  
**Then**:
- The file is stored (local volume for MVP)
- The file path is saved in the student record
- The file is accessible for viewing/download by instructors

### AC-7: Student Self-Service

**Given** a student is logged in  
**When** they view their profile  
**Then**:
- They can see all their information
- They cannot edit fields (instructor-only)
- They can see their attendance history (linked from Classes story)

## Domain Model References

### Student
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| user_id | UUID | FK to users (nullable) |
| name | VARCHAR(255) | Full name |
| phone | VARCHAR(20) | Contact phone |
| email | VARCHAR(255) | Email address |
| address | TEXT | Full address |
| cpf | VARCHAR(14) | Brazilian CPF |
| contractor | VARCHAR(255) | Parent/guardian |
| medical_certificate_url | VARCHAR(500) | PDF file path |
| previous_grade | VARCHAR(50) | Previous belt grade |
| current_belt_id | UUID | FK to belts |
| status | ENUM | active, inactive, graduated |
| photo_url | VARCHAR(500) | Photo file path |
| emergency_contact | VARCHAR(255) | Emergency contact |
| enrollment_date | DATE | Date of joining |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

## UI Requirements

- Student list page with search, pagination, and filters (by belt, status)
- Student detail/edit page with all fields
- Medical certificate upload component
- Student self-service profile view (read-only)
- Status badge (active/inactive/graduated)

## API Requirements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/students` | List students (paginated, searchable) | Instructor: all; Student: own |
| GET | `/api/students/{id}` | Get student details | Instructor: any; Student: own |
| POST | `/api/students` | Create student | Instructor |
| PUT | `/api/students/{id}` | Update student | Instructor |
| PATCH | `/api/students/{id}/status` | Change student status | Instructor |
| POST | `/api/students/{id}/medical-certificate` | Upload medical certificate | Instructor |

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| PR-1-auth | Internal | Requires user authentication and org scoping |
| PR-3-belts | Internal (future) | Belt assignment references belt table (can use placeholder initially) |

## Technical Notes

- Students are linked to user accounts via `user_id` (nullable for students without login)
- File uploads stored on persistent volume for MVP (object storage deferred)
- All queries scoped by `org_id` from authenticated user's token
