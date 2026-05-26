# Story 07-01: Events Management

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-7-events

## User Story

As an **instructor**, I want to create and manage dojo events (seminars, workshops, special training), so that students can be informed and their participation is tracked.

As a **student**, I want to see upcoming events and mark my attendance, so that my event participation counts toward my belt requirements.

## Acceptance Criteria

### AC-1: Create Event

**Given** an instructor is on the events page  
**When** they create a new event  
**Then** they can configure:
- Event name
- Description
- Date and time
- Location
- Maximum participants (optional)
- Whether the event is required or optional
- The event is scoped to their organization

### AC-2: View Events

**Given** a student or instructor is authenticated  
**When** they view the events list  
**Then**:
- They see upcoming and past events
- Each event shows: name, date, time, location, required/optional status
- Events are sorted by date (upcoming first)
- Past events are still visible for attendance history

### AC-3: Event Attendance

**Given** an event exists  
**When** attendance is recorded  
**Then**:
- The attendance record has `activity_type = "event"`
- For required events: instructors can mark attendance for all students
- For optional events: students can self-mark attendance
- The attendance counts toward `event` belt requirements
- Attendance can be recorded before, during, or after the event

### AC-4: Participant Limit

**Given** an event has a maximum participant limit  
**When** a student attempts to mark attendance  
**Then**:
- If the limit is not reached, attendance is recorded
- If the limit is reached, the student is added to a waitlist (or shown an error)
- Instructors can override the limit

### AC-5: Update Event

**Given** an instructor views an event  
**When** they edit the event  
**Then**:
- All fields can be updated
- Changes are reflected immediately
- Existing attendance records are not affected

### AC-6: Cancel Event

**Given** an event exists  
**When** an instructor cancels it  
**Then**:
- The event is marked as cancelled
- Students cannot mark new attendance
- Existing attendance records are preserved

## Domain Model References

### Event
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| name | VARCHAR(255) | Event name |
| description | TEXT | Event description |
| date | DATE | Event date |
| time | TIME | Event start time |
| location | VARCHAR(255) | Event location |
| max_participants | INT | Maximum participants (null for unlimited) |
| is_required | BOOLEAN | Whether attendance is mandatory |
| is_cancelled | BOOLEAN | Whether the event is cancelled |
| created_at | TIMESTAMP | Creation timestamp |

Attendance reuses the **Attendance** model with `activity_type = "event"`.

## UI Requirements

- Events list (upcoming and past, with required/optional badges)
- Event creation/edit form with all fields
- Event detail view with attendance list
- Attendance marking interface (self-service for optional, instructor-managed for required)
- Participant count indicator (current vs. max)

## API Requirements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/events` | List events (paginated, filterable) | Authenticated |
| POST | `/api/events` | Create event | Instructor |
| GET | `/api/events/{id}` | Get event details | Authenticated |
| PUT | `/api/events/{id}` | Update event | Instructor |
| PATCH | `/api/events/{id}/cancel` | Cancel event | Instructor |
| GET | `/api/events/{id}/attendance` | Get event attendance | Authenticated |
| POST | `/api/attendance` | Mark event attendance | Student (optional), Instructor (any) |

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| PR-2-students | Internal | Event attendance links to students |
| PR-9-eligibility | Internal (future) | Attendance counts toward event requirements |

## Technical Notes

- Events are a separate activity type from classes (no recurring schedule)
- Required vs. optional affects who can mark attendance
- Participant limit is a soft constraint — instructors can override
- Events do not have a class type (general/graduated) — all students can attend
