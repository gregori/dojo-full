# Pre-Check-in API

Base path: `/api/v1/pre-checkins`.

Pre-check-in records an intention to attend; it never creates official attendance. A physical tablet, QR, or manual check-in remains required.

## Public endpoints

`GET /events` lists scheduled events more than one hour away. It returns only `id`, `title`, `start_datetime`, `end_datetime`, and `location`.

`POST /confirm` and `POST /cancel` accept `{ "event_id", "registration_number", "pin" }`. Both rate-limit by IP and registration number. Invalid credentials receive the same generic accepted response as valid requests, without disclosing student information.

Confirmation changes are unavailable one hour before the event and for non-scheduled events. An optional event `minimum_belt_id` is evaluated against the student's belt ordering.

## Instructor/admin endpoints

- `GET /events/{event_id}/count` returns the number of confirmed pre-check-ins.
- `GET /events/{event_id}` returns the confirmed roster.

These endpoints require instructor or admin authentication.

## Lifecycle

`confirmed` → `cancelled` → `confirmed`, or `confirmed` → `converted` after physical attendance. There is one record per student/event. Rescheduling an event into its one-hour cutoff cancels current confirmations.
