---
name: squad-review
description: Run deterministic checks and a read-only independent review.
---

# Squad review

Run lint, test, and Git status gates first. Then invoke the reviewer directly with read-only access; the root must not review the implementation itself. Record findings and evidence in the run state; never use the reviewer to edit fixes.
