---
name: squad-test
description: Run deterministic tests and optionally author missing tests.
---

# Squad test

Run the test-runner gate first. Only invoke the platform's tester or test-author directly when a bounded test gap remains; the root must not author tests itself. The test specialist may write tests in its scope but does not modify production code without an explicit root instruction.
