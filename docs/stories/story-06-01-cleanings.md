# Story 06-01: Cleaning Groups

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-6-cleanings

## User Story

As an **instructor**, I want to create and manage cleaning groups, so that dojo maintenance responsibilities are distributed fairly among students.

As a **student**, I want to know when I'm assigned to a cleaning group, so that I can fulfill my cleaning duties and they count toward my belt requirements.

## Acceptance Criteria

### AC-1: Create Cleaning Group

**Given** an instructor is on the cleaning groups page  
**When** they create a new cleaning group  
**Then**:
- The group has a name and schedule (day of week or specific dates)
- The group composition follows the rule: 1 yudansha (≥ Azul) + 5-6 coloridas (below black belt)
- The instructor assigns specific students to the group
- The group is scoped to the instructor's organization

### AC-2: Group Composition Validation

**Given** an instructor is assigning students to a cleaning group  
**When** they add students  
**Then**:
- The system validates that exactly 1 yudansha (belt ≥ Azul, order ≥ 5) is assigned
- The system validates that 5-6 coloridas (belt < Dan) are assigned
- Warnings are shown if the composition is incorrect, but the instructor can override

### AC-3: Cleaning Attendance

**Given** a cleaning group has a scheduled cleaning  
**When** attendance is recorded  
**Then**:
- The attendance record has `activity_type = "cleaning"`
- Attendance can be marked by the instructor (not self-service)
- The attendance counts toward `cleaning` belt requirements
- There is **no blocking** — students are not prevented from other activities if they miss cleaning

### AC-4: View Cleaning Groups

**Given** an instructor or student  
**When** they view cleaning groups  
**Then**:
- Instructors see all groups with their members and schedules
- Students see only the groups they are assigned to
- Each group shows: name, members, schedule, attendance history

### AC-5: Edit Cleaning Group

**Given** an instructor views a cleaning group  
**When** they edit the group  
**Then**:
- They can add or remove students
- They can change the schedule
- Composition validation is re-applied on save
- Changes are reflected immediately

### AC-6: Deactivate Cleaning Group

**Given** an instructor views a cleaning group  
**When** they deactivate it  
**Then**:
- The group is marked as inactive
- No new attendance can be recorded
- Historical attendance records are preserved

## Domain Model References

### CleaningGroup
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| name | VARCHAR(255) | Group name |
| schedule | JSON | Schedule config (day of week, time, or specific dates) |
| is_active | BOOLEAN | Whether the group is active |
| created_at | TIMESTAMP | Creation timestamp |

### CleaningGroupMember
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| group_id | UUID | FK to cleaning_groups |
| student_id | UUID | FK to students |
| role | ENUM | yudansha, colorida |
| created_at | TIMESTAMP | Assignment timestamp |

Attendance reuses the **Attendance** model with `activity_type = "cleaning"`.

## UI Requirements

- Cleaning groups list with status indicators
- Group creation/edit form with student assignment
- Composition validation display (yudansha count, coloridas count)
- Group detail view with members and attendance history
- Schedule display (weekly or specific dates)

## API Requirements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/cleaning-groups` | List cleaning groups | Authenticated |
| POST | `/api/cleaning-groups` | Create cleaning group | Instructor |
| GET | `/api/cleaning-groups/{id}` | Get group details + members | Authenticated |
| PUT | `/api/cleaning-groups/{id}` | Update group | Instructor |
| POST | `/api/cleaning-groups/{id}/members` | Add member to group | Instructor |
| DELETE | `/api/cleaning-groups/{id}/members/{member_id}` | Remove member from group | Instructor |
| POST | `/api/attendance` | Mark cleaning attendance | Instructor |

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| PR-2-students | Internal | Groups contain students |
| PR-3-belts | Internal | Yudansha eligibility check (≥ Azul) |
| PR-9-eligibility | Internal (future) | Attendance counts toward cleaning requirements |

## Technical Notes

- Cleaning groups do **not** block other activities — missing cleaning has no automatic consequence
- The yudansha requirement (≥ Azul) ensures at least one experienced student per group
- Group composition is validated but can be overridden by the instructor
- Attendance is instructor-recorded only (not self-service)
