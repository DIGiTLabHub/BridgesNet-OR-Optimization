# Code Review Return Note

Paused on 2026-08-07 at Git commit `d0ffc03` (`main`). This note records the restart point; it is not a substitute for the requested review response.

## Governing task

Use `CODE_REVIEW_REQUEST.md` as the checklist and structure for the final feedback. The deliverable must answer its numbered requests with evidence, qualifications, and explicit pending items. It should not merely summarize repository changes.

Do not edit the manuscript or response letter as part of the code review unless that scope is separately authorized.

## Repository state at pause

- `CODE_REVIEW_FEEDBACK.md` is deleted in the current working tree. Before resuming, determine whether that deletion is intentional and either retain it or restore/rebuild the feedback deliberately.
- The reusable implementation, scenario runner, scalability driver, tests, and static review evidence are tracked in the current repository history.
- The corrected model includes the earliest-start constraints. Its default pre-presolve count is therefore 3,267 constraints; the historical 3,177 count describes the earlier model without those 90 constraints.
- Full-size optimization and presolve were blocked by the installed size-limited Gurobi license. No base-case, Pareto, sensitivity, or scalability solution should be called solver-certified until rerun under an adequate license.

## Evidence boundary for the sensitivity costs

The archived Gantt charts were inspected as their original PNG files in `ASCE_submission/Revision01/Figures/`, not as PDF-derived data. The images visibly establish bridge, depot, team, and approximate start/completion assignments. They do not display total costs, bridge BFI values, solver status, objective bounds, or gaps.

The totals in `review_evidence/reconstructed_sensitivity_summary.csv` combine assignments manually transcribed from those PNGs with the current seeded input data and cost formula:

| Scenario | Manuscript value | Figure/code reconstruction | Status |
|---|---:|---:|---|
| Service times `(1,2,2)` | $20,700 | $25,770 | Not solver-certified |
| Due dates reduced by one day | $42,080 | $42,090 | Not solver-certified |
| Initial BFI increased by 0.10 | $48,309 | $48,310 | Not solver-certified |

These reconstructed totals show an inconsistency that needs a rerun; they are not replacement results. In particular, the current two-decimal-thousand-dollar rounding produces costs in $10 increments, so it cannot produce $48,309.

Relevant evidence files:

- `review_evidence/reconstructed_sensitivity_schedules.csv`
- `review_evidence/reconstructed_sensitivity_summary.csv`
- `review_evidence/extract_static_evidence.py`
- `review_evidence/base_case_inputs.csv`
- `review_evidence/reconstructed_base_schedule.csv`
- `review_evidence/reconstructed_base_cumulative_profile.csv`
- `review_evidence/travel_time_matrix_hours.csv`
- `review_evidence/travel_time_matrix_days.csv`
- `review_evidence/shortest_paths.csv`
- `review_evidence/authoritative_run.log`

## Restart sequence

1. Check `git status` and resolve the intended status of `CODE_REVIEW_FEEDBACK.md` without discarding unrelated user changes.
2. Confirm that Gurobi has an adequate license, then record the license type, Python/Gurobi/package versions, hardware, and exact Git commit used for the runs.
3. Run the focused test suite:

   ```bash
   conda run -n bridgesnet python -m pytest -q
   ```

4. Run the authoritative base case and retain the model, logs, solution tables, status, incumbent, bound, gap, and runtime:

   ```bash
   conda run -n bridgesnet python scripts/run_analysis.py \
     --cities 6 --seed 2 --planning-horizon 8 \
     --output-dir results/review-base --pareto --write-lp
   ```

5. Run all named manuscript scenarios from the same base network and retain their input and solution records:

   ```bash
   conda run -n bridgesnet python scripts/run_sensitivity_analysis.py \
     --cities 6 --seed 2 --planning-horizon 8 \
     --scenarios base,service_time_1_2_2,due_minus_1,initial_bfi_plus_0_10 \
     --output-dir results/review-sensitivity --write-lp
   ```

6. Run the documented replicated scalability protocol only when the runtime is acceptable:

   ```bash
   conda run -n bridgesnet python scripts/run_sensitivity_analysis_scalability.py \
     --instances 15:2,30:2,45:3,60:4 --replications 10 \
     --seed-start 20260806 --planning-horizon 8 \
     --time-limit 3600 --mip-gap 0.0001 --threads 10 \
     --gurobi-seed 20260806 --output-dir results/review-scalability
   ```

7. Rebuild `CODE_REVIEW_FEEDBACK.md` around all 14 requested review sections. For each claim, distinguish code inspection, static reconstruction, unit tests, actual optimization, and remaining manual checks.

## Intentionally pending

The user does not plan to rerun the code now to update manuscript figures and tables. Therefore, regeneration of Figs. 3--11, numerical replacement in Tables 2--3, and corresponding manuscript/response-letter edits remain explicitly pending. Until those runs occur, preserve the archived numbers as unverified historical claims and report the reconstructed discrepancies only as diagnostic evidence.

