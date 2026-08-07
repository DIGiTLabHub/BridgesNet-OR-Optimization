# Code Review Request for the Revised Bridge-Recovery Manuscript

## Purpose

Please review the authoritative Python/Gurobi implementation underlying the revised manuscript and return evidence that confirms, corrects, or qualifies the implementation-dependent statements listed below.

This is primarily a verification task. Do not edit the manuscript or response letter during this review. If code changes are required to reproduce or diagnose a result, describe them separately and preserve the original implementation.

## Files that define the claims to be checked

- Revised manuscript: `Revision01/main-asce-format-revision01.tex`
- Response letter: `Revision01/Response_letter.tex`
- Bibliography: `Revision01/References-updated.bib`

No Python files or notebooks are currently present in this manuscript folder. Before beginning the technical review, please identify the authoritative implementation, input data, and figure-generation scripts supplied in the other session or workspace.

## Required review record

At the beginning of the feedback, report:

- Exact paths or repository URLs for the reviewed code and input data.
- Git commit hash, archive date, or another version identifier.
- Main executable script or notebook and the command used to run it.
- Python version, Gurobi version, operating system, processor, and available memory.
- Important package versions.
- Gurobi parameters that differ from their defaults, including time limits, random seeds, thread counts, and optimality tolerances.
- Whether any code or data had to be modified to complete the review.

## Priority 1: Formulation-to-code correspondence

### 1. Sets, indices, and network arcs

Confirm the actual implementation of the following sets:

- All network nodes, bridge nodes, city/intersection nodes, depot nodes, teams, and time points.
- Whether the base case contains 21 total nodes, 15 bridges, 2 depots, 3 team types, and eight indexed time points, `T = {0,...,7}`.
- Whether the routing model creates all `21 x 20 = 420` candidate directed arcs or only a restricted feasible arc set.
- Whether routing variables are created for every arc, depot, and team combination.
- Whether restoration-assignment variables are created for every bridge, time point, depot, and team combination.
- Whether service-start variables are created only for bridges or also for depots and other nodes.

If the code uses a different index structure from the manuscript, report the exact structure and the manuscript equations or notation that must be corrected.

### 2. Variable and constraint counts

Verify the manuscript's closed-form counts and the implemented model statistics before presolve:

- Routing binaries: `|A||D||K|`.
- Restoration-assignment binaries: `|B||T||D||K|`.
- Total binaries: `3,240` for the base case.
- Continuous service-start variables: `|B||D||K| = 90` for the base case.
- Total implemented constraints: `3,177` for the base case.

Return the following directly from Gurobi before optimization and, separately, after presolve if available:

- `NumVars`
- `NumBinVars`
- `NumIntVars`
- `NumConstrs`
- `NumNZs`
- Presolved rows and columns

Explain any discrepancy between the closed-form counts and Gurobi's reported model statistics. In particular, state whether the manuscript's `3,177` constraints are original-model or presolved-model constraints.

### 3. Decision-variable time semantics

Determine from the code whether `y[i,t,d,k] = 1` means that restoration:

- starts in period `t`,
- is active during period `t`, or
- is completed in period `t`.

The revised manuscript currently defines `y` as a completion-period variable and uses Eqs. (9) and (10) to impose `s_i^{dk} + theta_k = t` when `y_{it}^{dk} = 1`. Confirm that this is exactly what the code implements.

Also confirm:

- The units of `s`, `t`, `theta`, and travel time `eta`.
- Whether `a_i` is an earliest start time.
- Whether `b_i` is a latest completion time.
- Whether the code prevents work from extending beyond the seven-day horizon.

### 4. Routing, depot, flow, and subtour logic

Check the code against Eqs. (5) through (13), with special attention to the following questions:

- Do Eqs. (7) and (8), or their code equivalents, force every depot-team combination to leave and return exactly once, even when that team has no bridge assignment?
- Are inactive teams permitted? If so, how are depot departure and return constraints conditioned on team use?
- Are routes required to return to their originating depot?
- Are flow-conservation constraints imposed at bridges, city/intersection nodes, and depots as needed?
- Can a routing path legally pass through unserviced bridges or intermediate city nodes?
- Can disconnected arcs, unused cycles, or subtours occur?
- Does the time-progression constraint eliminate subtours for every relevant arc?

The current Eq. (11) includes `i` in the full node set while `s_i^{dk}` is described as a bridge service-start variable. Confirm how the code handles the case in which `i` is a depot or another nonbridge node. State whether Eq. (11), the definition of `s`, or both need revision.

### 5. Objective functions and Pareto procedure

Confirm that the code implements:

- Final average network functionality exactly as defined in Eq. (2), including the initial BFI contribution of unselected bridges.
- Total restoration cost exactly as defined in Eq. (3).
- The budget or epsilon constraint exactly as defined in Eq. (14).
- An epsilon-constraint solution procedure rather than a weighted-sum or native Gurobi multiobjective procedure.

Report:

- The epsilon values used.
- The number of optimization subproblems solved.
- The objective optimized in each subproblem.
- How dominated or duplicate solutions are removed.
- Solver status, incumbent objective, best bound, and optimality gap for each reported Pareto point.
- Whether the phrase "global optimality" is justified for every reported base-case and Pareto solution.

## Priority 2: Base-case data and reported results

### 6. Input parameters and derived bridge values

Confirm the code values and units for:

- Team service-time vector `(1,1,1)` days.
- Team base-cost vector `($1,000, $2,000, $5,000)`.
- Cost-adjustment parameter `alpha = 0.5`.
- Team BFI increments `delta_k`.
- Bridge-specific initial BFI values, restoration time windows, and derived restoration costs.
- Post-restoration BFI calculation `min(xi_i + delta_k, 1)`.

Check every row of manuscript Table 1 against the input data and calculations. Return a machine-readable CSV or Markdown table showing the implemented input values and the recalculated costs and post-restoration BFI values.

### 7. Travel times and shortest paths

Confirm:

- How each travel time `eta_ij` is obtained.
- Whether the code actually runs Dijkstra's algorithm.
- Whether the input represents distance, free-flow time, assumed speed, or another quantity.
- Any distance-to-time conversion and its units.
- Whether travel times are fixed and deterministic throughout a run.
- Whether travel between every candidate node pair is directly allowed or derived from shortest paths on an underlying road graph.

Provide the travel-time matrix used in the base case and identify the code lines that construct it.

### 8. Base-case solution

Rerun the authoritative base case and verify:

- Solver status and final optimality gap.
- Total restoration cost.
- Final average network functionality.
- Number and identities of restored and unrestored bridges.
- Depot and team assigned to every restored bridge.
- Route sequence for every deployed team.
- Service start and completion time for every restored bridge.
- Whether all time windows, sequencing constraints, and depot-return requirements are satisfied.

Specifically check the manuscript claims that:

- 13 of 15 bridges are restored.
- `BC5C60` and `BC3C60` are not selected in the base case.
- The maximum-functionality Pareto solution is approximately `0.791` at `$50,050`.
- The minimum reported Pareto value is `0.516` at `$20,920`.
- The example assignments and times described in the Objective and Routing Results and Gantt Chart Analysis subsections match the solver output.

Return one canonical solution table with one row per selected bridge and columns for bridge, depot, team, route position, start time, completion time, initial BFI, restored BFI, and cost.

### 9. Cumulative functionality and cost profiles

Verify that Fig. 5 is generated from the same base-case solution reported elsewhere and that its values follow the manuscript definitions:

- `F(t)` begins at the average initial post-event BFI.
- A bridge's realized BFI increment is added at its completion time, not at its start time.
- `C(t)` adds the corresponding restoration cost at the same completion time.
- The final values of `F(t)` and `C(t)` equal the base solution's final functionality and total cost.
- Daily plotted markers and any connecting lines are created consistently with the discrete-time model.

Return a table containing `t`, bridges completed at `t`, incremental functionality, cumulative `F(t)`, incremental cost, and cumulative `C(t)`. Flag every discrepancy between this table, the Gantt chart, the trajectory figure, and the prose.

## Priority 3: Sensitivity analyses

### 10. Service-time variation

Rerun the case with service times changed from `(1,1,1)` to `(1,2,2)` days and verify:

- All other inputs and constraints remain unchanged.
- 9 bridges are restored.
- Total cost is `$20,700`.
- Final average network functionality is `0.59`.
- The routes, assignments, and Gantt-chart times in Figs. 6 and 7 match the solver output.

### 11. Reduced restoration deadlines

Rerun the case in which each latest completion deadline `b_i` is reduced by one day while `a_i` is unchanged and verify:

- The resulting time windows remain valid.
- 11 bridges are restored.
- Total cost is `$42,080`.
- Final average network functionality is `0.72`.
- The routes, assignments, and Gantt-chart times in Figs. 8 and 9 match the solver output.

### 12. Increased initial BFI

Determine exactly how the average initial BFI is increased from approximately `0.32` to `0.42`:

- Is a constant added to every bridge BFI?
- Are values rescaled or replaced?
- Are values capped at 1?
- Are restoration costs and post-restoration BFIs recalculated afterward?

Rerun the scenario and verify:

- 13 bridges are restored.
- Total cost is `$48,309`.
- Final average network functionality is `0.86`.
- Higher initial BFI reduces the damage-adjusted restoration cost under Eq. (1).
- The routes, assignments, and Gantt-chart times in Figs. 10 and 11 match the solver output.

For all three sensitivity cases, return the same canonical solution table requested for the base case, plus a one-row summary with solver status, runtime, gap, bridge count, total cost, and final functionality.

## Priority 4: Pending scalability experiment

### 13. Experimental protocol

Design and document a reproducible scalability experiment for instances with:

| Damaged bridges | Depots |
|---:|---:|
| 15 | 2 |
| 30 | 2 |
| 45 | 3 |
| 60 | 4 |

Before running the experiment, specify:

- How synthetic networks, time windows, BFIs, travel times, and costs are generated.
- Number of teams per depot and whether it remains fixed across sizes.
- Planning-horizon length and discretization.
- Random seed and number of replications per size.
- Gurobi version, parameters, thread count, hardware, and common solver time limit.
- Whether each reported runtime and gap represents one maximum-functionality problem, one fixed-epsilon problem, or the complete Pareto-front procedure.
- If the complete Pareto procedure is used, how runtime and gap are aggregated across subproblems.

Do not mix single-run and complete-procedure runtimes in the same table.

### 14. Scalability results required for manuscript Table 3

Return a completed table with:

| Bridges (`B`) | Depots (`D`) | Binary variables | Continuous variables | Constraints | Runtime (s) | Gap (%) | Solver status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 15 | 2 |  |  |  |  |  |  |
| 30 | 2 |  |  |  |  |  |  |
| 45 | 3 |  |  |  |  |  |  |
| 60 | 4 |  |  |  |  |  |  |

Also provide enough evidence to determine:

- The largest instance solved to the specified optimality tolerance within the time limit.
- The first instance with a nonzero final gap or time-limit termination.
- Whether the results support recommending heuristic or hybrid methods beyond a particular instance size.
- Whether the current wording in the Computational Scalability and Exact-Solution Performance subsection should be retained, qualified, or revised.

## Priority 5: Figure-generation consistency

### 15. Regenerated figures

Identify the scripts and solution files used to generate Figs. 3 through 11. Confirm that regenerated figures:

- Use days consistently for all time axes.
- Use "network functionality" rather than "resilience" for the modeled objective and cumulative profile.
- Use the same team encoding for RRU, ERT, and CIRS across routing and Gantt figures.
- Remain interpretable in grayscale through line styles, markers, or patterns rather than color alone.
- Match the verified routes, assignments, start times, completion times, costs, and functionality values.

Report whether each current figure is reproducible directly from code. If a figure was manually edited, identify the manual steps and recommend how to make its generation reproducible.

## Required feedback format

Create a file named `CODE_REVIEW_FEEDBACK.md` with the following structure:

1. **Executive summary**: confirmed claims, corrected claims, unresolved items, and manuscript-blocking issues.
2. **Environment and code provenance**: all items requested under Required review record.
3. **Check-by-check findings**: use the same numbered headings as this request.
4. **Claim verification table** with columns:

   | Claim or manuscript location | Status (`confirmed`, `incorrect`, `qualified`, or `not reproducible`) | Code evidence | Numerical evidence | Recommended manuscript action |
   |---|---|---|---|---|

5. **Canonical solution tables** for the base case and three sensitivity cases.
6. **Cumulative-profile table** for the base case.
7. **Completed scalability table and experimental protocol**.
8. **Figure consistency table** for Figs. 3 through 11.
9. **Exact proposed corrections**, if needed, stated separately for:
   - `Revision01/main-asce-format-revision01.tex`
   - `Revision01/Response_letter.tex`
10. **Generated evidence files**: list all solver logs, CSV files, figures, and scripts created during verification.

For every numerical confirmation, cite the responsible code file and line or function name and attach the corresponding solver log or exported table. Do not mark a claim as confirmed solely because the current figures or manuscript state the same value.
