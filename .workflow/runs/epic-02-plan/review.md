# Requirements Review — Epic 2

## Recommendation

Epic 2 is sequenced for delivery but is not ready for unqualified implementation. Phase 1 can proceed after its short decision gate; later phases require the stated product-policy decisions.

## Findings

| Area | Finding | Planning response |
|---|---|---|
| PRE-04 | Cancellation threshold, notification behavior, and treatment of existing confirmations were unspecified. | Keep instructor cancellation discretionary; define state behavior before build. |
| PRE-05 | Physical check-in conversion did not define duplicate/idempotent behavior. | Require a single transaction and exactly one attendance. |
| Public access | PIN route needs generic errors, rate limits, and no student-list disclosure. | Add as Phase 1 acceptance criteria. |
| Time/state | Cutoff, timezone, reschedules, cancelled/started/finished events were incomplete. | Add a state matrix and reschedule decision gate. |
| Reporting order | Financial reports preceded financial data. | Deliver finance before reports. |
| Contracts | Contract fields require plan/value/frequency before finance defined their source. | Deliver contracts after financial foundation. |
| Documents | Upload/storage security and lifecycle were unspecified. | Establish shared document policy in Phase 2. |
| Finance | Billing, pricing, payments, and overdue rules are not yet testable. | Define policy before Phase 3. |

## Phase 1 Decision Gate

1. Event-state/reschedule rules.
2. Student eligibility rule.
3. Public endpoint security and privacy behavior.
4. `Event` as the canonical scheduled class entity.
