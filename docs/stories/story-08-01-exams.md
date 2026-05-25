# Story 08-01: Exams Management

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-8-exams

## User Story

As an **instructor**, I want to record exam sessions with all relevant details (candidates, ukes, board notes, correction reports), so that there is a complete record of each student's exam performance and the board's feedback.

As a **student**, I want to see my exam history and any correction reports, so that I understand what I need to improve for my next exam.

## Acceptance Criteria

### AC-1: Create Exam Record

**Given** an instructor is on the exams page  
**When** they create a new exam record  
**Then** they can configure:
- Exam date
- Location
- Examiners (list of instructors on the board)
- Start time and end time
- The exam is scoped to their organization

### AC-2: Add Candidates

**Given** an exam record exists  
**When** an instructor adds candidates  
**Then**:
- Each candidate is linked to a student
- The candidate's current belt is recorded at exam time
- The candidate's target belt (the belt they're testing for) is recorded
- The candidate's result is recorded: pass, fail, or pending

### AC-3: Add Ukes

**Given** an exam record exists  
**When** an instructor adds ukes  
**Then**:
- Each uke is linked to a student
- The uke's belt is recorded
- The uke's participation counts toward `exam_as_uke` belt requirements
- A student can be both a candidate and a uke in the same exam

### AC-4: Record Board Notes

**Given** an exam is in progress or completed  
**When** an instructor records board notes  
**Then**:
- Notes can be recorded per candidate
- Notes are free-text (the board's observations)
- Notes are visible to the candidate (student) after the exam

### AC-5: Generate Correction Report

**Given** an exam is completed  
**When** the board finalizes the exam  
**Then**:
- A correction report is generated per exam
- The report contains the board's feedback for each candidate
- The report is stored and accessible for viewing/download
- Candidates can see their own correction report

### AC-6: View Exam History

**Given** a student or instructor  
**When** they view exam history  
**Then**:
- Instructors see all exams with candidates, ukes, and results
- Students see only exams they participated in (as candidate or uke)
- Each exam shows: date, location, examiners, candidates, results
- Correction reports are accessible from the exam detail view

### AC-7: Exam Schedule

**Given** an exam is scheduled  
**When** the exam has start and end times  
**Then**:
- The schedule is visible to all authenticated users
- Candidates know when to arrive
- The schedule can be updated by instructors

## Domain Model References

### Exam
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| date | DATE | Exam date |
| location | VARCHAR(255) | Exam location |
| examiners | JSON | List of examiner names/IDs |
| start_time | TIME | Exam start time |
| end_time | TIME | Exam end time |
| correction_report_url | VARCHAR(500) | Path to correction report file |
| created_at | TIMESTAMP | Creation timestamp |

### ExamCandidate
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| exam_id | UUID | FK to exams |
| student_id | UUID | FK to students |
| current_belt_id | UUID | Belt at exam time |
| target_belt_id | UUID | Belt being tested for |
| result | ENUM | pass, fail, pending |
| board_notes | TEXT | Board's notes for this candidate |
| created_at | TIMESTAMP | Creation timestamp |

### ExamUke
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| exam_id | UUID | FK to exams |
| student_id | UUID | FK to students |
| belt_id | UUID | Uke's belt at exam time |
| created_at | TIMESTAMP | Creation timestamp |

## UI Requirements

- Exams list (past and upcoming)
- Exam creation form with date, location, examiners, schedule
- Exam detail view with candidates, ukes, board notes
- Candidate management (add/remove, set result, add notes)
- Uke management (add/remove)
- Correction report upload/view
- Student exam history view

## API Requirements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/exams` | List exams | Authenticated |
| POST | `/api/exams` | Create exam | Instructor |
| GET | `/api/exams/{id}` | Get exam details | Authenticated |
| PUT | `/api/exams/{id}` | Update exam | Instructor |
| POST | `/api/exams/{id}/candidates` | Add candidate | Instructor |
| PUT | `/api/exams/{id}/candidates/{cand_id}` | Update candidate (result, notes) | Instructor |
| POST | `/api/exams/{id}/ukes` | Add uke | Instructor |
| DELETE | `/api/exams/{id}/ukes/{uke_id}` | Remove uke | Instructor |
| POST | `/api/exams/{id}/correction-report` | Upload correction report | Instructor |
| GET | `/api/exams/{id}/correction-report` | Download correction report | Authenticated |
| GET | `/api/students/{id}/exams` | Get student's exam history | Student (own), Instructor (any) |

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| PR-3-belts | Internal | Belt references for candidates and ukes |
| PR-9-eligibility | Internal (future) | Uke participation counts toward exam_as_uke requirements |
| PR-10-promotion | Internal (future) | Exam results feed into promotion decisions |

## Technical Notes

- Correction reports are stored as files (PDF) on persistent volume for MVP
- Board notes are per-candidate, not per-exam
- A student can be both candidate and uke in the same exam
- Exam results (pass/fail) are recorded by the instructor, not automatic
- The `exam_as_uke` requirement type is satisfied by ExamUke records
