# District outbreak notifications — TDD evidence

## Source

The journeys and acceptance criteria came from the attached district-outbreak implementation request supplied for this task.

## User journeys

- Farmers receive a warning when the same crop disease is reported by at least three distinct farms in their district during the last 14 days.
- Repeated reports from one farm cannot manufacture an outbreak.
- Community alerts disclose crop and disease only, never another farmer or farm identity.
- The scheduled job computes the cross-user aggregate once and fans it out efficiently.
- Ongoing outbreaks can notify again weekly without sending a new alert every day.

## RED and GREEN evidence

- RED: `pytest tests/test_disease_outbreak_notifications.py -v` failed during collection because `OutbreakView` and `collect_outbreak` did not exist.
- GREEN: the same focused command passed all five tests after the minimal implementation.
- Regression: the selected disease and notification matrix passed 115 tests, skipped one artifact-dependent test, and produced one unrelated Starlette deprecation warning.
- Locale/type check: `npx.cmd tsc --noEmit` passed.

## Test specification

| # | Guarantee | Test | Type | Result |
|---|---|---|---|---|
| 1 | Many reports from only one or two distinct farms do not reach the threshold | `test_repeated_reports_from_one_or_two_farms_never_reach_threshold` | DB integration | PASS |
| 2 | Three distinct farms trigger one district event whose payload has only crop and disease | `test_three_distinct_farms_trigger_identity_free_outbreak_event` | DB/source integration | PASS |
| 3 | The scheduled job invokes the district aggregate exactly once for multiple users | `test_job_runs_district_aggregate_exactly_once_for_many_users` | Job integration | PASS |
| 4 | A report older than the 14-day window does not count | `test_report_older_than_window_does_not_reach_threshold` | DB integration | PASS |
| 5 | Deduplication is stable on different days in one week and changes the next week | `test_outbreak_dedup_key_is_stable_within_week_and_changes_next_week` | Unit | PASS |

## Coverage and known gaps

The focused suite directly executes the aggregate SQL, source fan-out, pure collector, and job call-count seam. No external delivery provider or network is involved. The broader module matrix remained green. A repository-wide numeric coverage report was not requested or run.

## Checkpoints

No Git checkpoint commits were created because the shared worktree already contains extensive unrelated and untracked user changes; committing would mix ownership and task scope. RED/GREEN evidence is preserved above instead.
