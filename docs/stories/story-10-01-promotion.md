# Story 10-01: Promotion System

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-10-promotion

## User Story

As an **instructor**, I want to manually confirm a student's belt promotion after verifying their eligibility and exam results, so that the student's belt is officially updated and the promotion is recorded in the system.

As a **student**, I want to see my promotion history, so that I can track my progression through the belt ranks.

## Acceptance Criteria

### AC-1: Initiate Promotion

**Given** a student has passed an exam and meets eligibility requirements  
**When** an instructor initiates a promotion  
**Then**:
- The system shows the student's current belt and target belt
- The system shows the eligibility check result
- The system shows the exam result (must be "pass")
- The instructor confirms the promotion

### AC-2: Promotion Confirmation

**Given** an instructor confirms a promotion  
**When** the promotion is submitted  
**Then**:
- The student's `current_belt_id` is updated to the new belt
- A promotion record is created with:
  - Student ID
  - Previous belt ID
  - New belt ID
  - Exam ID (the exam that qualified them)
  - Promoted by (instructor user ID)
  - Promotion date
- The student's status is updated if promoted to "graduated" (Dan)

### AC-3: Manual Process

**Given** the promotion system  
**When** a promotion occurs  
**Then**:
- Promotion is **always manual** — never automatic
- The instructor must explicitly confirm each promotion
- The system can suggest promotions (based on eligibility + exam pass) but does not execute them automatically

### AC-4: Promotion History

**Given** a student or instructor views promotion history  
**When** they inspect a student's record  
**Then**:
- They see all promotions for that student
- Each promotion shows: date, previous belt, new belt, exam, promoting instructor
- Students can see their own promotion history
- Instructors can see all students' promotion history

### AC-5: Promotion Validation

**Given** an instructor attempts to promote a student  
**When** the promotion is submitted  
**Then** the system validates:
- The student has passed an exam for the target belt
- The target belt is the next belt in the hierarchy (no skipping)
- The instructor has permission to promote (instructor role)
- If validation fails, an error is shown with details

### AC-6: Graduated Status

**Given** a student is promoted to Dan (1º Dan or higher)  
**When** the promotion is confirmed  
**Then**:
- The student's status is updated to "graduated"
- The student gains access to graduated training sessions (if not already eligible)
- The student may be eligible for yudansha responsibilities (e.g., cleaning group yudansha role)

## Domain Model References

### Promotion
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| student_id | UUID | FK to students |
| previous_belt_id | UUID | Belt before promotion |
| new_belt_id | UUID | Belt after promotion |
| exam_id | UUID | FK to exams (the qualifying exam) |
| promoted_by | UUID | FK to users (instructor who confirmed) |
| promotion_date | DATE | Date of promotion |
| notes | TEXT | Optional notes from instructor |
| created_at | TIMESTAMP | Creation timestamp |

## UI Requirements

- Promotion initiation page (showing eligibility, exam result, confirmation)
- Promotion confirmation dialog (with validation warnings)
- Promotion history view (per student)
- Student belt display (updated after promotion)
- Suggested promotions list (students who are eligible + passed exam but not yet promoted)

## API Requirements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/promotions` | Create promotion (confirm belt upgrade) | Instructor |
| GET | `/api/promotions` | List promotions (filterable) | Instructor |
| GET | `/api/students/{id}/promotions` | Get student's promotion history | Student (own), Instructor (any) |
| GET | `/api/promotions/suggested` | List suggested promotions (eligible + passed) | Instructor |

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| PR-8-exams | Internal | Exam results (must be "pass") |
| PR-9-eligibility | Internal | Eligibility verification |
| PR-3-belts | Internal | Belt hierarchy for validation |
| PR-2-students | Internal | Student belt update |

## Technical Notes

- Promotion is a manual, explicit action — no automation
- The promotion record serves as an audit trail
- Belt hierarchy validation prevents skipping belts
- The `promoted_by` field tracks which instructor confirmed the promotion
- Suggested promotions are computed (eligibility + exam pass - already promoted)
- After promotion, the student's eligibility is recalculated for the next belt
