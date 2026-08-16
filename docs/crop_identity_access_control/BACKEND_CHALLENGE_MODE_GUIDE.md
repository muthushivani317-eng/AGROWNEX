# Backend challenge mode

Use `make_backend_pipeline_adapter` with a controlled test environment URL,
an `internal_tester` or `pilot_tester` expected role, and a token provider that
returns a verified test token at runtime.

The adapter calls the real authenticated endpoint and records HTTP status,
resolved role, authorization outcome, crop-ID outcome, disease-dispatch status,
reason code, and latency. Tokens are never returned or written to reports.
Missing tester identity, role mismatch, HTTP failure, runtime failure, or
canonical manifest failure stops evaluation.

No real challenge images are included by this implementation.
