# Story 03-01: Belt System and Requirements

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-3-belts

## User Story

As an **instructor**, I want to configure belt requirements for each grade level, so that the system can automatically track whether students meet the criteria for exams and promotion.

As an **instructor**, I want to view the belt hierarchy and requirements, so that I can understand what each student needs to progress.

## Acceptance Criteria

### AC-1: Belt Hierarchy

**Given** the system is initialized  
**When** belt data is seeded  
**Then** the following belts exist:

| Kyu | Name | Color | Order |
|-----|------|-------|-------|
| 6 | 6º Kyu | Branca (White) | 1 |
| 5 | 5º Kyu | Amarela (Yellow) | 2 |
| 4 | 4º Kyu | Roxa (Purple) | 3 |
| 3 | 3º Kyu | Verde (Green) | 4 |
| 2 | 2º Kyu | Azul (Blue) | 5 |
| 1 | 1º Kyu | Marrom (Brown) | 6 |
| Dan | 1º Dan+ | Preta (Black) | 7 |

### AC-2: Belt Requirements Configuration

**Given** an instructor views belt requirements  
**When** they configure requirements for a belt  
**Then** they can set minimum counts for each requirement type:

| Requirement Type | Description |
|-----------------|-------------|
| `training_general` | Minimum general class attendances |
| `training_graduated` | Minimum graduated training attendances |
| `event` | Minimum event participations |
| `cleaning` | Minimum cleaning duty participations |
| `exam_as_uke` | Minimum times serving as uke in exams |

### AC-3: No Time Window

**Given** a belt requirement is configured  
**When** the system counts a student's progress  
**Then**:
- Requirements have **no time window** — the system counts total occurrences
- A student who attended 10 classes 2 years ago still has those counted
- There is no "reset" period for requirements

### AC-4: View Belt Requirements

**Given** an instructor or student views a belt  
**When** they inspect the requirements  
**Then** they see:
- The belt name, color, and order
- All configured requirement types with minimum counts
- For students: their current progress toward each requirement

### AC-5: Eligibility Thresholds

**Given** the belt hierarchy  
**When** checking special eligibility  
**Then**:
- Yudansha (black belt track) eligibility: student must be ≥ Azul (2nd Kyu, order ≥ 5)
- Graduados (graduated training) eligibility: student must be ≥ Roxa (4th Kyu, order ≥ 3)

### AC-6: Belt Assignment to Students

**Given** an instructor is managing a student  
**When** they assign or change a student's belt  
**Then**:
- The student's `current_belt_id` is updated
- The belt change is recorded with a timestamp
- The student's eligibility is recalculated based on the new belt's requirements

## Domain Model References

### Belt
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| name | VARCHAR(50) | Belt name (e.g., "6º Kyu", "1º Dan") |
| color | VARCHAR(50) | Color name (e.g., "Branca", "Preta") |
| kyu_level | INT | Kyu number (6-1) or null for Dan |
| is_dan | BOOLEAN | True for Dan belts |
| order | INT | Sort order (1-7) |
| created_at | TIMESTAMP | Creation timestamp |

### BeltRequirement
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| org_id | UUID | FK to orgs |
| belt_id | UUID | FK to belts |
| requirement_type | ENUM | training_general, training_graduated, event, cleaning, exam_as_uke |
| minimum_count | INT | Minimum occurrences required |
| created_at | TIMESTAMP | Creation timestamp |

## UI Requirements

- Belt hierarchy view (visual representation of the Kyu system)
- Belt requirement configuration page (instructor only)
- Per-belt detail page showing requirements
- Student belt progress indicator (showing count vs. minimum for each requirement type)

## API Requirements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/belts` | List all belts | Authenticated |
| GET | `/api/belts/{id}` | Get belt details + requirements | Authenticated |
| POST | `/api/belts` | Create belt (seeded by default) | Super-admin |
| PUT | `/api/belts/{id}` | Update belt | Super-admin |
| GET | `/api/belts/{id}/requirements` | Get requirements for a belt | Authenticated |
| POST | `/api/belts/{id}/requirements` | Set requirement for a belt | Instructor |
| PUT | `/api/belts/{id}/requirements/{req_id}` | Update requirement | Instructor |

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| PR-2-students | Internal | Belts are assigned to students |
| PR-9-eligibility | Internal (future) | Requirements are used by eligibility checker |

## Technical Notes

- Belts are seeded on first run with the standard Kyu hierarchy
- Requirements are configurable per organization (different dojos may have different requirements)
- Belt order is used for eligibility comparisons (higher order = higher rank)
- The `exam_as_uke` requirement type is unique — it tracks serving as uke, not taking the exam
