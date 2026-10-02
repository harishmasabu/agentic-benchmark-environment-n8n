# INC-001 — Production Checkout Incident

A deployment was released approximately 20 minutes ago.

Customers can browse products normally, but some checkout requests are now returning HTTP 500 errors.

Investigate and resolve the incident.

Your responsibilities are to:

1. Determine the root cause.
2. Determine which checkout requests are affected.
3. Use the available repository and incident evidence to support your conclusion.
4. Implement the smallest safe fix.
5. Verify that the previously failing checkout path works.
6. Verify that previously successful checkout behavior still works.
7. Create incident_summary.md containing:
   - root cause
   - customer impact
   - fix applied
   - verification performed

Available evidence may include source code, application logs, deployment information, failed-order data, and tests.

Requirements:

- Do not modify verifier.py.
- Do not weaken existing tests.
- Avoid unrelated changes.
- Support important conclusions with evidence from the workspace.
