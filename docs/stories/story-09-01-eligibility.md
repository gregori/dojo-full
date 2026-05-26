# Story 09-01: Eligibility Checking

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-9-eligibility

## User Story

As an **instructor**, I want to automatically check whether a student meets the requirements for a belt exam, so that I can make informed decisions about exam eligibility without manual calculation.

As a **student**, I want to see my eligibility status for the next belt, so that I know what I still need to accomplish before I can test.

## Acceptance Criteria

### AC-1: Check Eligibility for Next Belt

**Given** a student has a current belt  
**When** their eligibility is checked for the next belt  
**Then**:
- The system retrieves the requirements for the target belt
- The system counts the student's actual occurrences for each requirement type
- The system compares actual counts against minimum required counts
- The result shows: eligible (all requirements met) or not eligible (with details on which requirements are missing)

### AC-2: Requirement Counting

**Given** eligibility is being calculated  
**When** the system counts occurrences  
**Then** it counts across all activity types:

| Requirement Type | Source |
|-----------------|--------|
| `training_general` | Attendance records with `activity_type = "class"` for general classes |
| `training_graduated` | Attendance records with `activity_type = "graduated_session"` |
| `event` | Attendance records with `activity_type = "event"` |
| `cleaning` | Attendance records with `activity_type = "cleaning"` |
| `exam_as_uke` | ExamUke records for the student |

### AC-3: No Time Window

**Given** a student's history  
**When** requirements are counted  
**Then**:
- **All** historical occurrences are counted (no date range filter)
- Attendance from any date in the past is included
- There is no "reset" or "expiration" of completed requirements

### AC-4: Eligibility Display

**Given** an instructor or student views eligibility  
**When** the eligibility check is displayed  
**Then** it shows:
- Target belt (next belt in hierarchy)
- For each requirement type:
  - Required minimum count
  - Actual count
  - Status: met or not met (with shortfall if not met)
- Overall eligibility status: eligible or not eligible

### AC-5: Eligibility for Yudansha

**Given** a student's belt level  
**When** checking yudansha (black belt track) eligibility  
**Then**:
- The student must have belt ≥ Azul (2nd Kyu, order ≥ 5)
- If below Azul, the system shows: "Yudansha eligibility requires belt ≥ Azul"
- If ≥ Azul, the system proceeds to check belt requirements

### AC-6: Eligibility for Graduados

**Given** a student's belt level  
**When** checking graduados (graduated training) eligibility  
**Then**:
- The student must have belt ≥ Roxa (4th Kyu, order ≥ 3)
- If below Roxa, the student cannot attend graduated sessions
- If ≥ Roxa, the student is eligible for graduated training

### AC-7: Eligibility Check for Exam Registration

**Given** an instructor is adding a candidate to an exam  
**When** the candidate's eligibility is checked  
**Then**:
- The system checks eligibility for the target belt
- If not eligible, a warning is shown (but the instructor can override)
- The eligibility check result is recorded with the exam registration

## Domain Model References

This story does not create new models — it aggregates data from:
- **Belt** and **BeltRequirement** (from PR-3)
- **Attendance** (from PR-4, PR-5, PR-6, PR-7)
- **ExamUke** (from PR-8)

### EligibilityResult (computed, not stored)
| Field | Type | Description |
|-------|------|-------------|
| student_id | UUID | The student being checked |
| target_belt_id | UUID | The belt they're checking eligibility for |
| is_eligible | BOOLEAN | Overall eligibility status |
| requirements | JSON | Per-requirement breakdown |
| checked_at | TIMESTAMP | When the check was performed |

## UI Requirements

- Eligibility dashboard per student (showing progress toward next belt)
- Visual progress bars for each requirement type (actual vs. required)
- Overall eligibility badge (eligible / not eligible)
- Eligibility check inline when adding candidates to exams
- Student self-service eligibility view (own progress only)

## API Requirements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/students/{id}/eligibility` | Check eligibility for next belt | Student (own), Instructor (any) |
| GET | `/api/students/{id}/eligibility/{belt_id}` | Check eligibility for specific belt | Student (own), Instructor (any) |
| POST | `/api/eligibility/check` | Batch eligibility check for multiple students | Instructor |

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| PR-3-belts | Internal | Belt requirements definition |
| PR-4-classes | Internal | General class attendance data |
| PR-5-graduated | Internal | Graduated session attendance data |
| PR-6-cleanings | Internal | Cleaning attendance data |
| PR-7-events | Internal | Event attendance data |
| PR-8-exams | Internal | Exam uke participation data |

## Technical Notes

- Eligibility is computed on-demand (not pre-calculated or cached)
- The computation aggregates across multiple tables and activity types
- No time window means the query is a simple COUNT with no date filter
- The eligibility check is idempotent — same input always produces same output
- Instructor override is allowed for exam registration (warning, not blocking)
