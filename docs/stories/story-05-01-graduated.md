# Story 05-01: Graduated Training Sessions

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-5-graduated

## User Story

As an **instructor**, I want to schedule and manage graduated training sessions (treinos de graduados), so that advanced students (≥ Roxa) can train together and their attendance is tracked separately from general classes.

As a **student** with belt ≥ Roxa, I want to attend graduated training sessions, so that my advanced training attendance counts toward my belt requirements.

## Acceptance Criteria

### AC-1: Create Graduated Session

**Given** an instructor is on the class management page  
**When** they create a graduated training session  
**Then**:
- The session has a name, date, and time
- The session type is "graduated"
- Only students with belt ≥ Roxa (4th Kyu, order ≥ 3) are eligible to attend
- The session is scoped to the instructor's organization

### AC-2: Eligibility Enforcement

**Given** a graduated training session exists  
**When** a student attempts to mark attendance  
**Then**:
- Students with belt ≥ Roxa can mark attendance
- Students below Roxa see an error: "Graduated training requires belt ≥ Roxa (4th Kyu)"
- Instructors can override and allow any student to attend

### AC-3: Attendance Tracking

**Given** a graduated training session  
**When** attendance is recorded  
**Then**:
- The attendance record has `activity_type = "graduated_session"`
- The attendance counts toward `training_graduated` belt requirements
- The attendance is visible in the student's history

### AC-4: View Graduated Sessions

**Given** an instructor or eligible student  
**When** they view the session list  
**Then**:
- They see all graduated sessions (past and future)
- Each session shows date, time, and attendance count
- Eligible students see only sessions they can attend

### AC-5: Cancel Graduated Session

**Given** a graduated training session exists  
**When** an instructor cancels it  
**Then**:
- The session is marked as cancelled
- Students cannot mark attendance
- Existing attendance records are preserved

## Domain Model References

Graduated sessions reuse the **Class** model with `class_type = "graduated"` and the **Attendance** model with `activity_type = "graduated_session"`.

No new models are required — this story extends the class and attendance models from PR-4.

## UI Requirements

- Graduated session list (filtered from general classes)
- Session creation form (same as class form, with type pre-set to "graduated")
- Attendance marking interface (with eligibility check)
- Eligibility indicator showing which students can attend

## API Requirements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/classes?type=graduated` | List graduated sessions | Authenticated |
| POST | `/api/classes` | Create graduated session | Instructor (type=graduated) |
| POST | `/api/attendance` | Mark attendance | Student (own, if eligible), Instructor (any) |

Reuses endpoints from PR-4-classes with type filtering.

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| PR-3-belts | Internal | Belt level check for eligibility (≥ Roxa) |
| PR-4-classes | Internal | Reuses class and attendance models |
| PR-9-eligibility | Internal (future) | Attendance counts toward training_graduated requirements |

## Technical Notes

- Graduated sessions are a subtype of classes — no separate model needed
- The eligibility check uses belt order: student's belt order must be ≥ 3 (Roxa)
- Attendance `activity_type` distinguishes graduated sessions from general classes for requirement counting
