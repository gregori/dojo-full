# Story 04-01: Classes and Attendance

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-4-classes

## User Story

As an **instructor**, I want to create and manage class schedules, so that students know when classes occur and I can track attendance.

As a **student**, I want to mark my own attendance for classes, so that my training record is up to date and I can track my progress toward belt requirements.

## Acceptance Criteria

### AC-1: Create Scheduled Class

**Given** an instructor is on the class management page  
**When** they create a new class  
**Then** they can configure:
- Class name
- Day of week and time (recurring weekly schedule)
- Class type: general or graduated
- Active/inactive status
- The class is scoped to their organization

### AC-2: Create Ad-Hoc Class

**Given** an instructor needs a one-time class  
**When** they create an ad-hoc class  
**Then**:
- The class has a specific date (not recurring)
- It can be of type general or graduated
- It can be cancelled independently

### AC-3: Cancel Class

**Given** a scheduled or ad-hoc class exists  
**When** an instructor cancels it  
**Then**:
- The class is marked as cancelled
- Students cannot mark attendance for a cancelled class
- Existing attendance records are preserved but flagged

### AC-4: Self-Service Attendance

**Given** a student is logged in  
**When** they view an active class for today  
**Then**:
- They can mark themselves as present
- The attendance record is created with: student_id, activity_type="class", activity_id, date, present=true
- They cannot mark attendance for a cancelled class
- They cannot mark attendance for a class in the future

### AC-5: Retroactive Attendance (Instructor Only)

**Given** an instructor is managing a class  
**When** they mark attendance for a student  
**Then**:
- They can mark attendance for any date (past or present)
- Students cannot perform retroactive attendance
- The attendance record includes who recorded it (for audit)

### AC-6: View Attendance History

**Given** a student or instructor views attendance  
**When** they filter by student and date range  
**Then**:
- They see all attendance records for that student
- Records show: date, activity type, activity name, present status
- Students can only see their own attendance
- Instructors can see all students' attendance

### AC-7: Class Type Enforcement

**Given** a class is of type "graduated"  
**When** a student attempts to mark attendance  
**Then**:
- Only students with belt ≥ Roxa (4th Kyu) can attend graduated classes
- Students below the threshold see an error message
- Instructors can override this restriction

## Domain Model References

### Class
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| name | VARCHAR(255) | Class name |
| class_type | ENUM | general, graduated |
| day_of_week | INT | 0-6 for recurring classes (null for ad-hoc) |
| time | TIME | Class start time (null for ad-hoc) |
| date | DATE | Specific date for ad-hoc classes (null for recurring) |
| is_recurring | BOOLEAN | True for weekly scheduled classes |
| is_cancelled | BOOLEAN | True if cancelled |
| created_at | TIMESTAMP | Creation timestamp |

### Attendance
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| student_id | UUID | FK to students |
| activity_type | ENUM | class, graduated_session, event, cleaning |
| activity_id | UUID | FK to the specific activity |
| date | DATE | Date of attendance |
| present | BOOLEAN | Whether the student was present |
| recorded_by | UUID | FK to users (who recorded this) |
| created_at | TIMESTAMP | Creation timestamp |

## UI Requirements

- Class schedule view (weekly calendar for recurring classes)
- Class creation/edit form (recurring and ad-hoc)
- Attendance marking interface (student self-service)
- Attendance management interface (instructor, with retroactive capability)
- Attendance history view with filters (by student, date range, activity type)
- Cancelled class indicator

## API Requirements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/classes` | List classes (recurring + ad-hoc) | Authenticated |
| POST | `/api/classes` | Create class | Instructor |
| PUT | `/api/classes/{id}` | Update class | Instructor |
| PATCH | `/api/classes/{id}/cancel` | Cancel class | Instructor |
| GET | `/api/classes/{id}/attendance` | Get attendance for a class | Authenticated |
| POST | `/api/attendance` | Mark attendance | Student (own), Instructor (any) |
| GET | `/api/students/{id}/attendance` | Get student attendance history | Student (own), Instructor (any) |

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| PR-2-students | Internal | Attendance links to students |
| PR-3-belts | Internal | Graduated class eligibility checks belt level |
| PR-9-eligibility | Internal (future) | Attendance counts toward belt requirements |

## Technical Notes

- `activity_type` in Attendance is a discriminator for different activity types
- Recurring classes generate attendance opportunities based on date
- Ad-hoc classes are single-date events
- Attendance records are immutable once created (no edits, only new records)
