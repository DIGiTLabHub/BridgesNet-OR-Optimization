# Code Review Feedback for the Revised Bridge-Recovery Manuscript

## 1. Executive summary

This review initially confirmed the default synthetic instance structure, Table 1 inputs, objective-expression formulas, completion-time meaning of `y`, epsilon-constraint architecture, and the **historical translated-model** counts of 3,240 binary variables, 90 continuous variables, and 3,177 constraints. An authorized post-review refactor has since implemented the manuscript earliest-start equation, so the corrected default model now has 3,240 binary variables, 90 continuous variables, and **3,267 constraints** before presolve. The refactor does **not** by itself confirm the manuscript's reported optimal solutions, Pareto points, sensitivity results, presolved dimensions, runtimes, gaps, or global-optimality claims; those require new runs with an adequate Gurobi license.

The original findings and their present implementation status are:

1. **Resolved in code:** the former main and sensitivity runners omitted `GRB.MAXIMIZE`. All `run_*` optimization paths now use one shared solver helper and explicitly maximize final network functionality.
2. **Resolved in code:** manuscript Eq. (13), `s_i^{dk} >= a_i`, was absent. `src/bridgesnet/model.py` now enforces earliest starts, and a license-compatible solve test checks the behavior.
3. Every depot-team combination is forced to depart and return exactly once. Inactive teams are not allowed. This differs from language suggesting deployment is optional.
4. The implemented routing index is a complete 21-node metric closure, but most `x` variables involving city nodes or non-origin depots are not linked to service, flow, time, or the objective. The manuscript instead describes `A` as the passable road-segment set. These are not the same arc set.
5. The base model cannot be optimized or presolved with the installed size-limited Gurobi license. No solver logs or solution files supporting the manuscript's historical results are present. “Global optimality” is therefore not currently auditable.
6. Archived sensitivity Gantt assignments recalculate to `$25,770`, `$42,090`, and—under the only evident `+0.10` BFI transformation—`$48,310`, rather than `$20,700`, `$42,080`, and `$48,309`. The current code stores costs in `$10` increments, so `$48,309` cannot be produced by it.
7. **Resolved in generators, not historical figures:** Fig. 5 used a one-period lag. The canonical cumulative-profile code now updates functionality and cost at the modeled completion period and exports the underlying CSV. The manuscript figure still must be regenerated.
8. **Partly resolved:** the runners now generate duration-aware Gantt charts, day-based axes, final-network-functionality terminology, and grayscale-supporting styles from exported tables. Historical Figs. 3–11 have not been regenerated under the corrected model.
9. **Implemented but not numerically run:** the scalability driver builds all four requested sizes and now uses the same corrected solver path. Optimization remains blocked by the installed size-limited license, so no runtime threshold for heuristics is supported.
10. The original `Bridge_Sensitivity.ipynb` remains an unexecuted historical source artifact. The maximization regression in the modular implementation is now fixed; the notebook's incomplete travel-time data should not be restored. Appendix A records the parity audit and original TODO, and Appendix B records the post-review implementation status.

At the time of the initial review, no implementation or input data were modified. The later authorized refactor changed the reusable modules, all essential `run_*` scripts, tests, and README as summarized in Appendix B. The notebook and manuscript source/results were not rewritten.

## 2. Environment and code provenance

### Reviewed artifacts

- Repository: `https://github.com/DIGiTLabHub/BridgesNet-OR-Optimization.git`
- Local repository: `/Users/chenzhiq/MyGitProjects/BridgesNet-OR-Optimization`
- Reviewed commit: `93edd97cb19d57e13656e6505c9b8d587bde6e05` (2026-03-23; `Limit tracked ASCE figures to README assets`)
- Core model: `src/bridgesnet/model.py`
- Graph/input generation: `src/bridgesnet/config.py`, `src/bridgesnet/graph.py`
- Travel times: `src/bridgesnet/paths.py`
- Pareto procedure: `src/bridgesnet/pareto.py`
- Solution extraction and plotting: `src/bridgesnet/results.py`, `src/bridgesnet/plots.py`
- Documented main executable: `scripts/run_analysis.py`
- Sensitivity executable: `scripts/run_sensitivity_analysis.py`
- Historical notebook: `Bridge_Sensitivity.ipynb`, last changed at commit `7c55dea14c45ec484c867b08b27d5dd50c604fc4` (2026-02-10)
- Revised manuscript: `ASCE_submission/Revision01/main-asce-format-revision01.tex`
- Response letter: `ASCE_submission/Revision01/Response_letter.tex`
- Bibliography: `ASCE_submission/References-updated.bib`
- Submission figures: `ASCE_submission/Revision01/Figures/`

The synthetic base-case “input data” are not stored in a standalone input file. They are generated at runtime by `build_graph(GraphConfig(n_cities=6, seed=2), TeamConfig())`. The Revision01 sources and figures are ignored by `.gitignore`, so commit `93edd97...` is not a version identifier for their current contents. Review-time SHA-256 hashes were recorded during inspection; key hashes are:

- Manuscript: `376b1be65513a5b2a0eaa69b076bf8ecc3828df1fe947cc3681aa14d29da70d2`
- Response letter: `9d8716dec2651c4a8d3ad4238307bfcd21de438269cf2bf3546f2aa43a3aa1be`
- Bibliography: `c3cc63526082eb29243475d80ec92ea95c848c394cb972661893cfc5692ee70c`
- Core model: `a6d312f59cfc202a0889bb43d505c1192c151e8eea741c3bbe1403ee86a032e3`

### Commands attempted

Documented authoritative run command:

```bash
conda run -n bridgesnet python scripts/run_analysis.py \
  --cities 6 --seed 2 --planning-horizon 8 \
  --output-dir /private/tmp/bridgesnet-review-baseline --pareto --write-lp
```

Result: failed before optimization with `GurobiError: Model too large for size-limited license`. See `review_evidence/authoritative_run.log`.

Static evidence command:

```bash
conda run -n bridgesnet python review_evidence/extract_static_evidence.py
```

Test command:

```bash
conda run -n bridgesnet python -m pytest -q
```

Initial result: `2 passed in 1.65s`. After the authorized refactor, the focused suite reports `11 passed`; it now includes small solved MILPs plus objective-sense, earliest-start, model-count, Pareto-evidence, named-scenario, cumulative-profile, scalability-driver, and duration-aware plotting checks. Large-instance optimization and end-to-end manuscript-result reproduction remain untested under the installed license.

### Runtime environment

- Python: 3.11.15 (conda-forge)
- Gurobi: 13.0.1, restricted size-limited non-production license
- OS: macOS 14.6.1, arm64
- Processor: Apple M1 Max, 10 cores (8 performance, 2 efficiency)
- Memory: 64 GB
- NetworkX: 3.6.1
- NumPy: 2.4.3
- Matplotlib: 3.10.8
- pytest: 9.0.2

No non-default Gurobi parameters are set in the original core, main-analysis, Pareto, or general sensitivity code. Observed defaults were `Threads=0` (automatic; Gurobi reported up to 10 threads), `TimeLimit=infinity`, `Seed=0`, `MIPGap=1e-4`, `MIPGapAbs=1e-10`, `FeasibilityTol=1e-6`, `IntFeasTol=1e-5`, and `OptimalityTol=1e-6`. The formulation sets `M=1000`, which is a model constant rather than a Gurobi parameter. Commented notebook lines mention `MIPGap=0.04` but do not apply it. The subsequently added scalability driver explicitly records and sets `TimeLimit`, `MIPGap`, `Threads`, `Seed`, and per-run logging parameters.

## 3. Check-by-check findings

### 1. Sets, indices, and network arcs

**Confirmed for the default generated instance:**

- All nodes: 21.
- Cities/intersections: `C1`–`C6`.
- Bridge nodes: `BC1C20`, `BC1C30`, `BC1C40`, `BC1C50`, `BC1C60`, `BC2C30`, `BC2C40`, `BC2C50`, `BC2C60`, `BC3C40`, `BC3C50`, `BC3C60`, `BC4C50`, `BC4C60`, `BC5C60`.
- Depots: `C1`, `C2` (subsets of city nodes, not additional nodes).
- Team types: `RRU`, `ERT`, `CIRS`; the code instantiates one of each type at each depot through six `(depot, team)` pairs.
- Time points: `range(8) = {0,...,7}`.

`model.py:64-70` creates routing variables for every ordered pair of distinct nodes, giving `21*20=420` candidate pairs for each of six depot-team combinations: 2,520 `x` binaries. This is the complete-node-pair metric closure, not the underlying physical road graph. The physical generated graph has only 60 directed edges; travel between candidate pairs is represented by a shortest-path travel time.

`y` exists only for bridges, each depot-team pair, and each time point (`15*6*8=720`). `s` exists only for bridges and each depot-team pair (`15*6=90`).

**Required correction:** distinguish the physical passable-road arc set from the complete reachable service-routing arc set. The manuscript currently defines `A` as physical road segments at lines 143–146 but uses `|A|=420` at line 344.

### 2. Variable and constraint counts

Direct Gurobi statistics after `model.update()` and before optimization:

| Statistic | Value |
|---|---:|
| `NumVars` | 3,330 |
| `NumBinVars` | 3,240 |
| `NumIntVars` | 3,240 |
| Continuous variables (`NumVars - NumIntVars`) | 90 |
| `NumConstrs` | 3,177 |
| `NumNZs` | 12,150 |
| Presolved rows | Not available: license rejected `Model.presolve()` |
| Presolved columns | Not available: license rejected `Model.presolve()` |

Constraint-count decomposition:

| Family | Count |
|---|---:|
| At most one restoration | 15 |
| Incoming route/assignment link | 90 |
| Outgoing route/assignment link | 90 |
| Depot departure | 6 |
| Depot return | 6 |
| Upper completion-time link | 720 |
| Lower completion-time link | 720 |
| Time progression | 1,440 |
| Due date | 90 |
| **Total** | **3,177** |

The manuscript's 3,177 is unequivocally the **original model before presolve**, not a presolved count.

### 3. Decision-variable time semantics

`y[i,dk,t]=1` means restoration is **completed** at indexed time `t`. `model.py:141-162` enforces `s[i,dk] + service_time[k] = t` whenever `y=1`, matching manuscript Eqs. (9)–(10).

- `s`, `t`, and `theta` are in days.
- Edge `Time = length/speed` is treated as hours and divided by 24 in `model.py:170` before addition to day-valued start times.
- `Start` is generated as the intended earliest start `a_i`, but it is never used by the modular model. The corresponding notebook constraint is commented out.
- `Due` is enforced as the latest completion `b_i` by `s+theta <= Due`.
- Selected service cannot complete after Day 7 because `y` only exists through `t=7`; generated due dates are also at most 7.
- Depot return travel and return time are not modeled, so the code does not establish that a team returns by the horizon.

Manuscript Eq. (13) and the assertions that full time windows are enforced are incorrect for the current implementation.

### 4. Routing, depot, flow, and subtour logic

- `model.py:124-139` forces every one of the six depot-team pairs to leave and return exactly once. A team cannot be inactive.
- Return is to the originating depot because each route uses `dk[0]` in both departure and return equalities.
- Meaningful flow conservation is imposed at restored bridges through the incoming/outgoing link equalities. It is not imposed at ordinary city nodes or at non-origin depots.
- Shortest paths may pass through city nodes and unserviced bridge nodes. This is consistent only with the stated assumption that all roadway links and noncollapsed bridges remain passable.
- `x` variables involving ordinary city nodes, or a depot other than `dk[0]`, are generally orphan variables: they are created but excluded from the assignment links, depot equations, and meaningful time constraints. They can take arbitrary binary values without changing objective or feasibility.
- For the linked route over the home depot and assigned bridge nodes, positive service time in the bridge-to-bridge progression constraints prevents a disconnected bridge-only subtour.
- Time progression does not constrain the return arc, so return-time feasibility is not verified.

Manuscript Eqs. (5)–(6) sum over all `V`, whereas the code sums only over bridges plus the route's home depot. Eq. (11) is also not a literal transcription: for bridge origins the code uses `s_i`; for any depot origin it substitutes zero because no depot `s` variable exists. Eq. (11) or the definition/domain of `s` must be revised, and the depot case must be written separately.

### 5. Objective functions and Pareto procedure

The expression `(resilience + resilience_raw)/bridges_count` exactly implements final average functionality, including initial BFI for unselected bridges (`model.py:192-205`). The cost expression matches Eq. (3) (`model.py:207-211`). `pareto.py` implements an epsilon cost constraint, not a weighted sum or native Gurobi multiobjective.

However:

- The main and sensitivity scripts omit `GRB.MAXIMIZE` and therefore minimize functionality.
- `pareto_frontier(..., num_epsilons=10)` solves 12 subproblems: maximum functionality, minimum cost, then 10 equally spaced epsilon budgets from the obtained minimum cost to the cost of the maximum-functionality incumbent.
- The epsilon values cannot be reported numerically without a successful run; they are not saved anywhere.
- Duplicate or dominated points are not removed.
- There is no secondary cost minimization at a fixed functionality level, so weakly efficient or duplicate points may remain.
- `pareto.py` records no status, incumbent, bound, gap, or runtime and accesses `ObjVal` without checking that a solution exists.
- `run_sensitivity_analysis.py` accepts `SUBOPTIMAL` but writes status `optimal`.

No base-case or Pareto point can presently be described as solver-certified globally optimal. The archived endpoints (`0.516/$20,920` and approximately `0.791/$50,050`) are consistent with the plotted labels and reconstructed base assignment but are not supported by retained solver evidence.

### 6. Input parameters and derived bridge values

Confirmed implemented parameters (`config.py:13-23`):

- Service times: `(1,1,1)` days.
- Base costs: `(1,2,5)` in thousands of dollars, represented in the manuscript as `$1,000`, `$2,000`, `$5,000`.
- `alpha=0.5`.
- `delta_RRU=0.30`, `delta_ERT=0.55`, `delta_CIRS=0.75`.
- Post-restoration BFI: `min(round(xi_i + delta_k, 2), 1)`.
- Cost: `round(base_cost_k * (1 + alpha*(1-xi_i)), 2)` in thousands of dollars.

Every Table 1 row matches the generated data and current formulas. The machine-readable audit is `review_evidence/base_case_inputs.csv`. Average initial BFI is `0.322`.

### 7. Travel times and shortest paths

`graph.py:73-98` samples an edge length and speed, then stores `Time=length/speed`. The code does not explicitly declare the length unit, although the values and speed choices imply miles and miles/hour; this unit interpretation is an inference, not encoded metadata. `model.py` treats the result as hours and divides by 24.

`paths.py:10-31` calls NetworkX weighted shortest-path functions for every ordered node pair. With nonnegative weights, NetworkX uses Dijkstra's method. Travel times are fixed and deterministic for a seed. All 420 service-routing pairs use shortest paths on the 60-edge underlying generated road graph; direct physical travel between every pair is not assumed.

The exact matrices are:

- `review_evidence/travel_time_matrix_hours.csv`
- `review_evidence/travel_time_matrix_days.csv` (the quantities actually inserted into the MILP)
- `review_evidence/shortest_paths.csv` (path sequence plus both units)

Historical notebook warning: its first bridge-edge block does not set the `Time` attribute, while the modular code does. NetworkX treats missing weighted-edge attributes as weight 1. The notebook and modular code therefore do not construct identical travel matrices.

### 8. Base-case solution

The authoritative run was blocked by the Gurobi license. Solver status, gap, bound, runtime, and global optimality are not reproducible.

The archived Fig. 4 and manuscript prose can nevertheless be reconstructed into the 13-bridge table in Section 5. That reconstruction:

- leaves `BC3C60` and `BC5C60` unrestored;
- totals `$50,050`;
- yields final average functionality `0.791333`;
- satisfies the displayed earliest starts, due dates, horizon completions, and chronological bridge-to-bridge sequencing under the current shortest-path matrix;
- does not prove that the table is a Gurobi solution or that it is optimal;
- cannot verify return-by-horizon because the model contains no return-time constraint.

The examples at manuscript lines 365–369 and 387–388 match Fig. 4's assignments/start times. They should be described as historical/archived results until reproduced with a solver log and solution export.

### 9. Cumulative functionality and cost profiles

The current repository has no function that generates `F(t)` or `C(t)`. `plots.py` provides only network, route, Gantt, and Pareto plotting. Fig. 5 is therefore not reproducible from current code.

The completion-time reconstruction in Section 6 begins at `0.322`, adds realized BFI increments and cost at completion, and ends at `0.791333/$50,050`. Fig. 5 instead remains flat through `t=3`, begins increasing at `t=4`, and ends near `0.748/$43,430`. This is exactly the profile before the Day-7 `BC2C40` completion and is consistent with a one-period plotting lag that drops the last completion.

Fig. 5 also retains “Resilience” in the title and y-axis and does not label the x-axis in days.

### 10. Service-time variation

No current script implements the `(1,2,2)` scenario or generates Figs. 6–7. Fig. 7 contains nine assignments, and their time bars are internally compatible with the stated durations and generated windows. Using the authoritative input costs, those assignments total `$25,770`, not `$20,700`; their final functionality is `0.594667`, consistent with the rounded `0.59` claim.

The original submission text also reported `$25.77` (apparently thousands), supporting the conclusion that `$20,700` in the revision is a transcription or recalculation error. This is figure/input evidence, not solver certification.

### 11. Reduced restoration deadlines

No current script implements this scenario or generates Figs. 8–9. Reducing every `Due` by one day leaves all generated windows valid. Fig. 9 contains eleven assignments that satisfy the reduced displayed deadlines and chronological sequencing. They recalculate to `$42,090` and functionality `0.727333`, rather than `$42,080` and `0.72` (the functionality agrees after coarse rounding; the cost differs by `$10`).

The archived original manuscript described reducing the **start time**, while the revised manuscript describes reducing the latest completion deadline. The figure is compatible with the revised deadline-minus-one interpretation, but the missing scenario code prevents provenance verification.

### 12. Increased initial BFI

No code defines how the mean BFI is increased. The only transformation consistent with retaining the same random draws and shifting the generated range from `(0.2,0.4)` to `(0.3,0.5)` is adding `0.10` to each BFI. For this instance that raises the mean from `0.322` to `0.422`; no value requires capping.

If costs and restored BFIs are recalculated afterward using current code, the 13 assignments shown in Fig. 11 yield final functionality exactly `0.860000` and cost `$48,310`. The claimed `$48,309` is impossible under the authoritative two-decimal-thousand-dollar cost rounding, which can only produce totals in `$10` increments.

The higher initial BFI does reduce the damage-adjusted cost for a fixed bridge-team pair, as Eq. (1) states. The transformation, recomputation order, and scenario code must be made explicit and rerun.

### 13. Experimental protocol

The following protocol is implemented by the separate `scripts/run_sensitivity_analysis_scalability.py` driver:

1. Keep six city/intersection nodes. Generate exactly `B/15` bridges on each of the 15 city pairs, giving 15, 30, 45, or 60 bridges and total node counts 21, 36, 51, and 66.
2. Fix depots deterministically to the first `D` city nodes (`C1...CD`) instead of relying on `depot_bias`, whose current implementation produces a random depot count.
3. Use current generation distributions: BFI uniform in `[0.2,0.4]` rounded to two decimals; earliest start in `{0,1,2}`; due offset in `{2,...,5}`; edge speed in `{60,80,120}`; edge length in the current integer ranges; current cost and restored-BFI formulas.
4. Compute all-pairs weighted shortest paths and use days in the MILP.
5. Keep one RRU, ERT, and CIRS per depot and `T={0,...,7}` for every size. State explicitly that current constraints force every one of these teams to deploy.
6. Use 10 replications per size with graph seeds `20260806` through `20260815`.
7. Use Gurobi 13.0.1 on the reviewed Apple M1 Max/64-GB machine with `Threads=10`, `TimeLimit=3600`, `MIPGap=1e-4`, and Gurobi `Seed=20260806`. Save one log, model-statistics record, and solution record per replication.
8. Measure **one maximum-final-functionality solve**, not the full Pareto procedure, in Table 3. Report median runtime across replications, maximum final gap, and status as `x/10 optimal; y/10 time limit`. If the full Pareto procedure is studied separately, report total wall time, number of subproblems, and maximum subproblem gap in a separate table.
9. The driver uses the shared explicit-`GRB.MAXIMIZE` solver path and records solution status, incumbent, bound, gap, runtime, cost, and restored-bridge count. Earliest starts are now enforced; mandatory deployment remains a documented formulation choice that the manuscript must state.

### 14. Scalability results required for manuscript Table 3

Model sizes below were instantiated directly with the protocol above. They were not optimized or presolved.

| Bridges | Depots | Binary variables | Continuous variables | Constraints | Runtime (s) | Gap (%) | Solver status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 15 | 2 | 3,240 | 90 | 3,267 | Not run | — | Statistics-only build succeeded |
| 30 | 2 | 9,000 | 180 | 9,222 | Not run | — | Statistics-only build succeeded |
| 45 | 3 | 26,190 | 405 | 27,198 | Not run | — | Statistics-only build succeeded |
| 60 | 4 | 57,240 | 720 | 59,844 | Not run | — | Statistics-only build succeeded |

No instance was solver-certified in this review; therefore there is no largest optimally solved instance, first nonzero-gap instance, or evidence-based heuristic threshold. The manuscript must retain Table 3 as explicitly pending or remove the subsection and any empirical scalability conclusions. The general statement that larger MILPs may motivate heuristics is reasonable, but it is not a result of this experiment.

### 15. Regenerated figures

See Section 8 for the figure-by-figure table. No Figs. 3–11 were regenerated successfully because optimization is blocked and the scenario/trajectory generators are missing. The copied Revision01 figures are byte-identical to the previously inspected repository copies.

## 4. Claim verification table

| Claim or manuscript location | Status | Code evidence | Numerical evidence | Recommended manuscript action |
|---|---|---|---|---|
| 21 nodes, 15 bridges, 2 depots, 3 teams, 8 time points | confirmed | `graph.py:27-100`; `model.py:50-60` | `static_summary.json` | Retain |
| `A=420` allowable road arcs | qualified | `model.py:64-70` creates 420 metric-closure pairs; generated graph has 60 edges | Model statistics | Define separate physical and service-routing arc sets |
| 3,240 binaries and 90 continuous variables | confirmed | `model.py:64-83` | Gurobi pre-optimization attributes | Retain and state “before presolve” |
| 3,177 constraints | superseded | Historical translation omitted 90 earliest-start constraints | Corrected `NumConstrs=3267` | Report 3,267 for the corrected model before presolve |
| `y` is completion-period binary | confirmed | `model.py:141-162` | `s+theta=t` when selected | Retain |
| Earliest starts `a_i` are enforced | resolved after review | `Earliest_Start` constraint family | Focused solve test and LP inspection | Retain Eq. (13); regenerate results |
| All teams may be inactive if unused | incorrect | `model.py:124-139` uses equality 1 | Six mandatory routes | Add activation binaries/conditional equalities or state mandatory deployment |
| Eq. (11) applies over all nodes with bridge-only `s` | incorrect | Code substitutes zero for depot and excludes ordinary cities | Static inspection | Write bridge and depot cases separately |
| Main executable maximizes final functionality | resolved after review | Shared `solve_maximum_functionality` path | Focused solve has `ModelSense=-1`; exported LP says `Maximize` | Rerun all reported results |
| Epsilon-constraint method is used | confirmed | `pareto.py:39-53` | 10 generated budgets; 12 solve calls total | Retain method description; add status logging/deduplication |
| Every Table 1 row matches code | confirmed | `config.py`; `graph.py:49-68` | `base_case_inputs.csv` | Retain |
| Base result is 13 bridges, `0.791`, `$50,050` | qualified | No retained solver result; archived schedule only | Reconstruction gives `0.791333/$50,050` | Rerun and attach log/solution before claiming optimality |
| Pareto minimum is `0.516/$20,920` | not reproducible | Pareto code saves no epsilon/status table | Figure label only | Rerun/export full point table |
| Service variation is 9 bridges, `0.59`, `$20,700` | incorrect | Scenario code absent | Fig. 7 assignments give `0.594667/$25,770` | Reconcile and rerun; do not retain `$20,700` |
| Deadline reduction is 11 bridges, `0.72`, `$42,080` | incorrect | Scenario code absent | Fig. 9 assignments give `0.727333/$42,090` | Reconcile and rerun |
| Increased BFI is 13 bridges, `0.86`, `$48,309` | incorrect | Transformation code absent; costs rounded to `$10` | `+0.10` reconstruction gives `0.860000/$48,310` | Define transformation and rerun |
| Fig. 5 adds changes at completion and reaches base final values | incorrect | No trajectory generator | Correct table ends `0.791333/$50,050`; figure ends about `0.748/$43,430` | Regenerate from exported `y` solution |
| Gurobi solved case study to global optimality | not reproducible | No status/bound/gap export; current license blocks solve | `authoritative_run.log` | Remove until solver-certified |
| Figs. 3–11 use days/functionality/grayscale-safe encoding | incorrect | `plots.py:61-143`; scenario generators absent | Direct visual inspection | Regenerate all affected figures |
| Scalability results support a heuristic threshold | not reproducible | Driver implemented; no solver results under the available license | All four static sizes build successfully | Run with an unrestricted license before making an empirical threshold claim |

## 5. Canonical solution tables

All tables in this section are **reconstructed from archived figures/manuscript prose and authoritative input formulas; they are not solver-certified**. Machine-readable copies are in `review_evidence/reconstructed_base_schedule.csv` and `review_evidence/reconstructed_sensitivity_schedules.csv`.

### Base case

| Bridge | Depot | Team | Route position | Start | Completion | Initial BFI | Restored BFI | Cost ($) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| BC1C20 | C1 | ERT | 1 | 2 | 3 | 0.32 | 0.87 | 2,680 |
| BC1C60 | C1 | ERT | 2 | 4 | 5 | 0.40 | 0.95 | 2,600 |
| BC4C60 | C1 | RRU | 1 | 2 | 3 | 0.39 | 0.69 | 1,300 |
| BC2C50 | C1 | RRU | 2 | 4 | 5 | 0.26 | 0.56 | 1,370 |
| BC4C50 | C1 | CIRS | 1 | 3 | 4 | 0.24 | 0.99 | 6,900 |
| BC2C30 | C1 | CIRS | 2 | 5 | 6 | 0.26 | 1.00 | 6,850 |
| BC3C50 | C2 | ERT | 1 | 3 | 4 | 0.35 | 0.90 | 2,650 |
| BC1C30 | C2 | ERT | 2 | 5 | 6 | 0.39 | 0.94 | 2,610 |
| BC2C60 | C2 | RRU | 1 | 2 | 3 | 0.35 | 0.65 | 1,320 |
| BC1C50 | C2 | RRU | 2 | 4 | 5 | 0.30 | 0.60 | 1,350 |
| BC3C40 | C2 | CIRS | 1 | 2 | 3 | 0.25 | 1.00 | 6,880 |
| BC1C40 | C2 | CIRS | 2 | 4 | 5 | 0.23 | 0.98 | 6,920 |
| BC2C40 | C2 | CIRS | 3 | 6 | 7 | 0.35 | 1.00 | 6,620 |

Unrestored: `BC3C60`, `BC5C60`. Reconstructed totals: 13 bridges, `$50,050`, final functionality `0.791333`.

### Service times `(1,2,2)`

| Bridge | Depot | Team | Route position | Start | Completion | Initial BFI | Restored BFI | Cost ($) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| BC2C60 | C2 | RRU | 1 | 2 | 3 | 0.35 | 0.65 | 1,320 |
| BC2C50 | C2 | CIRS | 1 | 3 | 5 | 0.26 | 1.00 | 6,850 |
| BC1C30 | C2 | ERT | 1 | 4 | 6 | 0.39 | 0.94 | 2,610 |
| BC2C30 | C2 | RRU | 2 | 5 | 6 | 0.26 | 0.56 | 1,370 |
| BC4C50 | C1 | RRU | 1 | 2 | 3 | 0.24 | 0.54 | 1,380 |
| BC1C40 | C1 | CIRS | 1 | 3 | 5 | 0.23 | 0.98 | 6,920 |
| BC1C50 | C1 | ERT | 1 | 3 | 5 | 0.30 | 0.85 | 2,700 |
| BC1C60 | C1 | RRU | 2 | 4 | 5 | 0.40 | 0.70 | 1,300 |
| BC2C40 | C1 | RRU | 3 | 6 | 7 | 0.35 | 0.65 | 1,320 |

Summary: solver status/runtime/gap unavailable; 9 figure assignments; recalculated cost `$25,770`; functionality `0.594667`.

### Latest completion deadlines reduced by one day

| Bridge | Depot | Team | Route position | Start | Completion | Initial BFI | Restored BFI | Cost ($) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| BC3C40 | C2 | CIRS | 1 | 2 | 3 | 0.25 | 1.00 | 6,880 |
| BC3C50 | C2 | ERT | 1 | 2 | 3 | 0.35 | 0.90 | 2,650 |
| BC5C60 | C2 | RRU | 1 | 2 | 3 | 0.35 | 0.65 | 1,320 |
| BC1C30 | C2 | RRU | 2 | 4 | 5 | 0.39 | 0.69 | 1,300 |
| BC1C60 | C2 | ERT | 2 | 4 | 5 | 0.40 | 0.95 | 2,600 |
| BC2C30 | C2 | CIRS | 2 | 4 | 5 | 0.26 | 1.00 | 6,850 |
| BC1C40 | C1 | ERT | 1 | 2 | 3 | 0.23 | 0.78 | 2,770 |
| BC2C60 | C1 | RRU | 1 | 2 | 3 | 0.35 | 0.65 | 1,320 |
| BC4C50 | C1 | CIRS | 1 | 2 | 3 | 0.24 | 0.99 | 6,900 |
| BC2C50 | C1 | CIRS | 2 | 4 | 5 | 0.26 | 1.00 | 6,850 |
| BC2C40 | C1 | ERT | 2 | 5 | 6 | 0.35 | 0.90 | 2,650 |

Summary: solver status/runtime/gap unavailable; 11 figure assignments; recalculated cost `$42,090`; functionality `0.727333`.

### Initial BFI increased by `+0.10` (inferred transformation)

| Bridge | Depot | Team | Route position | Start | Completion | Shifted BFI | Restored BFI | Cost ($) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| BC1C20 | C2 | ERT | 1 | 2 | 3 | 0.42 | 0.97 | 2,580 |
| BC3C40 | C2 | CIRS | 1 | 2 | 3 | 0.35 | 1.00 | 6,620 |
| BC4C60 | C2 | RRU | 1 | 2 | 3 | 0.49 | 0.79 | 1,250 |
| BC1C30 | C2 | RRU | 2 | 4 | 5 | 0.49 | 0.79 | 1,250 |
| BC1C40 | C2 | CIRS | 2 | 4 | 5 | 0.33 | 1.00 | 6,670 |
| BC1C50 | C2 | ERT | 2 | 4 | 5 | 0.40 | 0.95 | 2,600 |
| BC2C40 | C2 | CIRS | 3 | 6 | 7 | 0.45 | 1.00 | 6,380 |
| BC2C60 | C1 | ERT | 1 | 2 | 3 | 0.45 | 1.00 | 2,550 |
| BC4C50 | C1 | CIRS | 1 | 2 | 3 | 0.34 | 1.00 | 6,650 |
| BC5C60 | C1 | RRU | 1 | 2 | 3 | 0.45 | 0.75 | 1,270 |
| BC1C60 | C1 | RRU | 2 | 4 | 5 | 0.50 | 0.80 | 1,250 |
| BC2C30 | C1 | CIRS | 2 | 4 | 5 | 0.36 | 1.00 | 6,600 |
| BC2C50 | C1 | ERT | 2 | 4 | 5 | 0.36 | 0.91 | 2,640 |

Summary: solver status/runtime/gap unavailable; 13 figure assignments; recalculated cost `$48,310`; functionality `0.860000`.

## 6. Cumulative-profile table for the base case

Derived from the base table above using completion-time semantics:

| `t` (day) | Bridges completed at `t` | Incremental functionality | Cumulative `F(t)` | Incremental cost ($) | Cumulative `C(t)` ($) |
|---:|---|---:|---:|---:|---:|
| 0 | — | 0.000000 | 0.322000 | 0 | 0 |
| 1 | — | 0.000000 | 0.322000 | 0 | 0 |
| 2 | — | 0.000000 | 0.322000 | 0 | 0 |
| 3 | BC1C20; BC4C60; BC2C60; BC3C40 | 0.126667 | 0.448667 | 12,180 | 12,180 |
| 4 | BC4C50; BC3C50 | 0.086667 | 0.535333 | 9,550 | 21,730 |
| 5 | BC1C60; BC2C50; BC1C50; BC1C40 | 0.126667 | 0.662000 | 12,240 | 33,970 |
| 6 | BC2C30; BC1C30 | 0.086000 | 0.748000 | 9,460 | 43,430 |
| 7 | BC2C40 | 0.043333 | 0.791333 | 6,620 | 50,050 |

The machine-readable table is `review_evidence/reconstructed_base_cumulative_profile.csv`. Fig. 5 appears to plot the `t=3...6` values at `t=4...7`, dropping the final row.

## 7. Completed scalability table and experimental protocol

The static-size table is completed in Finding 14. Runtime, gap, and status cannot truthfully be completed because no solve was possible. The implemented protocol is in Finding 13 and `scripts/run_sensitivity_analysis_scalability.py`. `review_evidence/scalability_model_sizes.csv` contains total nodes, candidate arcs, nonzeros, and depot identities in addition to the manuscript columns.

## 8. Figure consistency table for Figs. 3–11

| Figure | Current source/code | Directly reproducible? | Consistency findings | Required action |
|---:|---|---|---|---|
| 3 Pareto | `plot_pareto`, `pareto_frontier` | No exact reproduction; no saved points/logs | Says “Resilience”; color-dependent; statuses/gaps absent | Export point CSV/logs; label final network functionality; add grayscale-safe markers |
| 4 Base Gantt | `plot_gantt` can plot an extracted schedule | Not end-to-end under current license | X-axis says “Time,” not days; color-only; schedule reconstructs to historical base totals | Regenerate from exported solution and label days |
| 5 Cumulative profile | No generator in repository | No | Says “Resilience”; no day unit; one-period lag; omits Day-7 completion/final totals | Implement from `y` completion periods and regenerate |
| 6 Service routes | No scenario route driver | No | Archived image only; color-only; no solution provenance | Implement scenario/export route arcs and regenerate |
| 7 Service Gantt | No scenario Gantt driver | No | Says “Time (hour)” although bars represent days; displayed cost sums to `$25,770` | Reconcile result, label days, regenerate |
| 8 Reduced-deadline routes | No scenario route driver | No | Archived image only; color-only; no solution provenance | Implement scenario/export route arcs and regenerate |
| 9 Reduced-deadline Gantt | No scenario Gantt driver | No | Says “Time (hour)”; displayed cost sums to `$42,090` | Reconcile result, label days, regenerate |
| 10 Increased-BFI routes | No scenario route driver | No | Transformation is undocumented; color-only | Define transformation, rerun, regenerate |
| 11 Increased-BFI Gantt | No scenario Gantt driver | No | Says “Time (hour)”; `+0.10` reconstruction gives `$48,310` | Reconcile result, label days, regenerate |

Team semantics are broadly consistent by hue (RRU blue, ERT orange/red, CIRS green), but shades differ and no route/Gantt plot uses line styles, markers, or hatch patterns. Red depot/green city encoding is especially weak in grayscale. `results.py:39-43` also aggregates active edges by team type rather than `(depot, team)`, reducing route provenance in plots.

## 9. Exact proposed corrections

### `ASCE_submission/Revision01/main-asce-format-revision01.tex`

1. **Arc definition and counts (lines 143–146 and 344):** replace the single `A` definition with a physical arc set and a service-routing metric closure, for example:

   > Let `A_0` denote passable directed road segments in the generated graph. For optimization, let `A={(i,j): i,j in V, i != j, and j is reachable from i in (V,A_0)}` denote the complete reachable service-routing arc set, with `eta_ij` equal to the shortest-path travel time on `A_0`. The base case has `|A_0|=60` and `|A|=420`.

2. **Incoming/outgoing equations (Eqs. 5–6):** change their summation domains from all `V` to the actual coded domain `B union {d}` for the route's originating depot, or revise the code to use a deliberately restricted `x` index and then rewrite the equations to that final implementation.

3. **Team activation (Eqs. 7–8):** either state explicitly that all three team types at every depot must deploy and each must service at least one bridge, or introduce `u_dk` and replace both right-hand sides with `u_dk`.

4. **Time progression (Eq. 11):** split the bridge and depot cases. If depots have no service duration, the logically consistent depot constraint is `s_j^{dk} >= eta_dj - M(1-x_dj^{dk})`; the current code instead adds `theta_k` at depot departure. Decide which behavior is intended, correct the code, and state it exactly. Add a return-time variable/constraint if return by Day 7 is claimed.

5. **Earliest start (Eq. 13):** implement `s_i^{dk} >= a_i` (preferably conditioned on assignment) before retaining lines 308–311 and related feasibility claims. Otherwise delete Eq. (13) and all statements that `a_i` is enforced.

6. **Implementation paragraph (line 342):** replace “Gurobi solved ... to global optimality” with:

   > The current repository defines the case-study model, but solver status, incumbent, bound, gap, and runtime must be reported from the archived verification run before an optimality claim is made.

7. **Count paragraph (line 344):** update it to the corrected implementation: “the Gurobi model before presolve contains 3,267 constraints and 12,240 nonzero coefficients; presolved dimensions are reported separately when available.”

8. **Base/Pareto results (lines 361–410):** retain the figures and numerical claims only after a corrected `GRB.MAXIMIZE` run exports status, objective, bound, gap, assignments, routes, and times. Until then, remove “optimal,” “global,” and “feasible” assertions or label the values as archived illustrative outputs awaiting reproduction.

9. **Fig. 5:** regenerate from the exported completion-period `y` variables. The correct reconstructed values are those in Section 6; the final marker must be `0.791333/$50,050` at Day 7.

10. **Sensitivity claims:** do not simply substitute the review reconstructions as solver-verified results. Reconcile and rerun. If the archived figure assignments are retained, the internally consistent values are `$25,770/0.594667`, `$42,090/0.727333`, and—after explicitly adding `0.10` to every BFI and recalculating—`$48,310/0.860000`.

11. **Table 3/scalability discussion:** keep runtime/gap/status as pending or remove Table 3 until the protocol is executed. Do not infer a heuristic threshold from variable counts alone.

12. **Figures:** replace “resilience” with “final network functionality” where appropriate, label all time axes in days, and add grayscale-safe styles/hatches. Regenerate from versioned CSV/solution files rather than manually copying images.

### `ASCE_submission/Revision01/Response_letter.tex`

1. At the response containing the formulation counts (around lines 103–117), replace the historical 3,177 with the corrected **pre-presolve** count of 3,267 and state that presolved dimensions/runtime/gap remain pending.
2. Do not imply the implementation has been fully verified or solved globally until the corrected maximization run and logs exist. Add the discovered implementation corrections—objective sense, earliest-start constraint, and team-activation interpretation—to the response if they change the revised equations or results.
3. The response around lines 169–193 says Fig. 5 reconstructs completion-event profiles. Add that the figure was regenerated from exported completion variables only after correcting the current one-period lag and missing final completion.
4. The graphics response at lines 201–207 currently describes future regeneration. Before submission, replace future tense with a completed-action description only after Figs. 3–11 actually use days, network-functionality terminology, consistent team encoding, and grayscale-safe distinctions. The supplied Revision01 figures do not yet satisfy that response.
5. Update the sensitivity-response text and any quoted values only after the reruns reconcile the three cost discrepancies documented above.

## 10. Generated evidence files

Created during this review:

- `CODE_REVIEW_FEEDBACK.md` — this report.
- `review_evidence/extract_static_evidence.py` — read-only evidence extractor; imports but does not modify authoritative code/data.
- `review_evidence/static_summary.json` — environment, sets, counts, defaults, and base metadata.
- `review_evidence/base_case_inputs.csv` — Table 1 audit.
- `review_evidence/travel_time_matrix_hours.csv` — all-pairs generated shortest-path times before day conversion.
- `review_evidence/travel_time_matrix_days.csv` — all-pairs times used in the MILP.
- `review_evidence/shortest_paths.csv` — paths and both units.
- `review_evidence/reconstructed_base_schedule.csv` — archived base schedule reconstruction, explicitly not solver-certified.
- `review_evidence/reconstructed_base_cumulative_profile.csv` — correct completion-time profile derived from the reconstruction.
- `review_evidence/reconstructed_sensitivity_schedules.csv` — figure-derived sensitivity schedules, explicitly not solver-certified.
- `review_evidence/reconstructed_sensitivity_summary.csv` — recalculated counts/costs/functionality.
- `review_evidence/scalability_model_sizes.csv` — instantiated pre-optimization model sizes.
- `review_evidence/figure_inventory.csv` — Revision01 figure paths, sizes, and hashes.
- `review_evidence/authoritative_run.log` — failed main-run attempt showing the size-limited-license blocker.
- `review_evidence/presolve_attempt.log` — failed presolve attempt showing the same blocker.
- `scripts/run_sensitivity_analysis_scalability.py` — subsequent standalone scalability driver with replicated generation, correct maximization sense, solver logging, instance snapshots, and aggregate tables.
- `tests/test_scalability_script.py` — focused tests for size parsing, exact graph/depot generation, deterministic snapshots, and aggregation.

No solver solution logs, incumbent files, Pareto CSVs, or regenerated submission figures could be created because optimization was blocked. During the original review, no manuscript, response letter, bibliography, core `src/` module, notebook, input data, or existing figure was modified. The subsequent authorized scalability work added its standalone driver and tests and updated the README; it did not change the core model or notebook.

## Appendix A. Original-notebook-to-refactor parity audit and code-revision TODO

### A.1 Status of the notebook as evidence

`Bridge_Sensitivity.ipynb` contains six cells: four code cells and two Markdown headings. Every code cell has `execution_count=None`, every cell has zero stored outputs, and the notebook metadata identifies only the Python language—not a Python version, package environment, Gurobi version, license, or hardware. It is therefore useful as historical source code but is **not** an executable record of any reported numerical result, solver status, figure, or Pareto point.

The notebook contains:

1. synthetic graph/data generation and a network plot;
2. all-pairs shortest paths, MILP construction, one base solve, and a route plot;
3. a base Gantt plot;
4. a ten-budget epsilon-constraint loop and Pareto plot.

It contains **no code** for the three manuscript sensitivity cases, cumulative trajectory Fig. 5, solution export, solver-log retention, or scalability analysis. Consequently, those parts of the reimplementation cannot be validated against this notebook.

### A.2 Parity matrix

| Area | Notebook behavior | Modular reimplementation | Assessment |
|---|---|---|---|
| Base parameters | Teams, costs, BFI increments, service times, `alpha`, six cities, seed 2 | `TeamConfig` and `GraphConfig` preserve these defaults | Faithful |
| Random generation | Global `random.seed(2)` | Local `random.Random(seed)` with the same call order | Faithful and safer; node order, node attributes, edge order, and non-time edge attributes match exactly |
| Depot selection | `biased_choice(0.90)` returns 1 when random value is at least 0.90 | Same inequality exposed as `depot_bias` | Faithful but misleading: 0.90 produces approximately 10% depots, not 90% |
| Edge travel time | Sets `Time` only on bridge-to-second-city segments; 30 of 60 directed edges lack `Time` | Sets `Time=length/speed` on all 60 directed edges | Intentional correction, but behavior-changing |
| Shortest paths | NetworkX silently assigns weight 1 to edges missing `Time` | Validates that every edge has `Time`, then computes weighted paths | Improvement; not numerically equivalent to notebook |
| Travel-time parity | Notebook-weight matrix ranges from about 0.0167 to 1.1833 hours | Corrected matrix ranges from about 0.0083 to 0.1667 hours | 352 of 420 ordered-pair times differ; 201 of 240 route-relevant pairs differ, affecting 1,206 of 1,440 time-progression RHS constants |
| Node/edge/variable sets | Complete ordered node-pair `x`; bridge-only `y` and `s` | Same | Faithful, including orphan `x` variables |
| Assignment, depot, completion, progression, and due constraints | Implements the same families | Implements the same families | Faithful, including original formulation defects |
| Earliest start | `s>=Start` block is commented out | Constraint omitted | Faithful to executed notebook code, but inconsistent with manuscript Eq. (13) |
| Base objective | Explicit `GRB.MAXIMIZE` | `run_analysis.py` omits objective sense | **Reimplementation regression: reverses the base objective** |
| General sensitivity objective | No general sweep exists in notebook | `run_sensitivity_analysis.py` also omits objective sense | **New script regression: minimizes functionality** |
| Scalability objective | No scalability code | New driver explicitly uses `GRB.MAXIMIZE` | Correct relative to intended base objective, but still inherits core-model defects |
| LP export | Writes once before all constraints and overwrites again before `setObjective`; retained `BRIDGE.lp` therefore lacks the intended objective | Optional main-script export occurs after objective setup/solve | Refactor improves export ordering, but its exported sense is still wrong until `GRB.MAXIMIZE` is restored |
| Base status handling | Handles only `INFEASIBLE`; otherwise reads solution values | Main script and extractor remain insufficiently defensive | Defect carried forward; time-limit/no-incumbent and other statuses are unsafe |
| Schedule extraction | Includes any `s` variable with value over 0.5 and parses its name | Checks the associated `y` assignment and uses dictionary keys | Improvement |
| Route extraction | Aggregates arcs by team type, discarding depot in the plotting key | Same | Faithful but loses route provenance |
| Gantt duration | Always draws bars of length 1 | Always draws bars of length 1 | Defect carried forward; wrong for non-unit service times |
| Team colors | Route and Gantt plots use different shades | Main script passes one color map to both | Improvement in current generated output; archived figures remain inconsistent |
| Network labels | City labels are numeric portions (`1`–`6`) | `node_labels()` returns blank labels for all nodes | Reimplementation regression in figure labeling |
| Pareto algorithm | Two endpoint solves plus ten epsilon solves; no status checks or deduplication | Same algorithm; removes each constraint via its returned object | Mostly faithful; constraint removal is improved, substantive Pareto defects remain |
| Terminology | Uses “Resilience” throughout plots/variables | Retains `resilience` names and labels | Defect carried forward relative to revised manuscript terminology |
| Sensitivity scenarios | Absent | General Cartesian parameter sweep, not the three manuscript scenarios | Missing reimplementation; manuscript scenarios remain provenance-free |
| Cumulative profile | Absent | Absent | Missing implementation; Fig. 5 cannot be regenerated |
| Automated parity tests | None | Tests cover graph/path basics and scalability helpers only | Missing; no golden model/solution parity suite |

### A.3 Interpretation

The notebook should not be treated as a gold-standard numerical implementation because its travel-time data are incomplete and it retains the same routing, earliest-start, team-activation, return-time, status, Pareto, and plotting weaknesses identified elsewhere in this review. Conversely, the refactor should not be treated as a behavior-preserving translation because it changes the travel matrix and accidentally changes the base objective from maximization to minimization.

The correct path is to define one authoritative formulation and data specification, repair it deliberately, and then establish new verified reference outputs. Attempting to make the modules reproduce the notebook's missing-edge travel weights would reproduce a notebook bug. Attempting to preserve every modular result would preserve the objective-sense regression and the notebook's original formulation defects.

### A.4 Prioritized TODO to revise the full codebase

#### P0 — Freeze an authoritative specification before rerunning results

- [ ] Preserve `Bridge_Sensitivity.ipynb` as a historical artifact; do not continue editing it as production code.
- [ ] Write a concise model specification identifying the physical road-edge set, service-routing metric closure, units, team availability, time-index semantics, start/due semantics, depot departure, and depot-return requirements.
- [ ] Decide and document that every physical edge must have `Time=length/speed`; retain the modular correction and explicitly invalidate notebook-derived travel matrices.
- [ ] Create one versioned base-instance file containing the exact 21-node graph, all node/edge attributes, team parameters, and seed/provenance rather than regenerating authoritative manuscript inputs implicitly on every run.
- [ ] Define canonical units in data names or typed fields (`length_miles`, `speed_mph`, `travel_hours`, `travel_days`, `cost_thousand_usd`) and remove implicit `/24` conversions from constraint expressions.
- [ ] Define expected output artifacts—model statistics, status, incumbent, bound, gap, assignments, ordered routes, start/completion times, costs, functionality, and logs—before another manuscript run.

#### P0 — Correct the core optimization model

- [ ] Add a single shared objective helper and require callers to pass an explicit sense; set the base, sensitivity, Pareto, and scalability maximum-functionality solves to `GRB.MAXIMIZE`.
- [ ] Implement and test earliest-start feasibility (`s_i^{dk} >= a_i` when assigned), resolving the manuscript/code mismatch.
- [ ] Decide whether teams may be inactive. If yes, add depot-team activation binaries and condition departure/return and assignment constraints; if no, state and test mandatory deployment explicitly.
- [ ] Separate physical road arcs from metric-closure service arcs and create `x` only on the intended routing domain. Remove orphan binaries involving ordinary city nodes and non-origin depots.
- [ ] Rewrite flow conservation over the final routing domain and verify that no disconnected paths, free cycles, or unused arcs can be selected.
- [ ] Split time progression into bridge-origin and depot-origin cases. Do not add bridge service duration to depot departure unless it represents a separately defined mobilization time.
- [ ] Add return-time propagation and enforce depot return within the planning horizon if return-by-horizon is claimed.
- [ ] Condition start/due constraints on assignment or otherwise define unassigned `s` values cleanly.
- [ ] Replace the fixed `M=1000` with valid, tighter bounds derived from the horizon, maximum service duration, and maximum travel time.
- [ ] Validate all input dictionaries and ranges: team keys, nonnegative durations/costs, BFI bounds, `Start<=Due`, finite paths, depot count, and planning horizon.

#### P1 — Consolidate solver execution and status handling

- [ ] Create one solver-run function used by every CLI. It must set the objective, parameters, log path, optimize, and return a structured result.
- [ ] Require `SolCount>0` before reading `X`, `ObjVal`, or expression values.
- [ ] Preserve exact Gurobi status instead of labeling `SUBOPTIMAL` as `optimal`; record runtime, incumbent, best bound, relative gap, and error text for every run.
- [ ] Handle `INFEASIBLE`, `INF_OR_UNBD`, `UNBOUNDED`, limits without incumbents, interruptions, numeric failures, and license errors explicitly.
- [ ] Export one machine-readable solution file and one solver log for every successful or partially successful solve.
- [ ] Write LP/MPS artifacts only after the complete model and explicit objective sense are set; verify the exported objective and sense on read-back.
- [ ] Make CLIs return nonzero on execution failures while retaining partial evidence files.
- [ ] Ensure main, Pareto, sensitivity, and scalability scripts use the same environment/provenance recorder.

#### P1 — Rebuild the three manuscript sensitivity scenarios explicitly

- [ ] Replace reliance on the unrelated Cartesian sweep with named scenario constructors for: base; service times `(1,2,2)`; `Due_i-1`; and initial `BFI_i+0.10`.
- [ ] Make every scenario a copy of one versioned base instance and change only the documented fields.
- [ ] For `Due_i-1`, validate that every revised window remains valid and record the changed values.
- [ ] For increased BFI, explicitly add 0.10 to each bridge, apply any cap, and recompute post-restoration BFI and cost in a documented order.
- [ ] Export scenario inputs before solving so the `$25,770/$20,700`, `$42,090/$42,080`, and `$48,310/$48,309` discrepancies can be resolved from primary evidence.
- [ ] Do not use the general parameter sweep as evidence for Figs. 6–11 unless it is extended to reproduce these exact named scenarios.

#### P1 — Repair the Pareto workflow

- [ ] Check status and incumbent availability after every endpoint and epsilon solve.
- [ ] Save the exact epsilon value, status, incumbent, bound, gap, runtime, functionality, cost, and solution identifier for every subproblem.
- [ ] Remove duplicate and dominated points using a stated numerical tolerance.
- [ ] Add a deterministic secondary objective or lexicographic tie-break so a functionality solution does not report an avoidably expensive weakly efficient point.
- [ ] Clarify whether the minimum-cost endpoint is meaningful when all depot-team pairs are forced to deploy.
- [ ] Report endpoint solves separately from the ten epsilon solves and avoid counting duplicated endpoint budgets as new Pareto alternatives.

#### P2 — Replace ad hoc result extraction with a canonical solution object

- [ ] Store active routes by `(depot, team)`, not team type alone.
- [ ] Reconstruct each route as an ordered sequence from its home depot, detect branching/cycles, and include return to depot.
- [ ] Store bridge, depot, team, route position, start, completion, initial BFI, restored BFI, realized increment, and cost in one canonical table.
- [ ] Validate every exported solution independently against assignment, flow, timing, window, horizon, and return constraints.
- [ ] Distinguish solver objective from derived final functionality and assert that they agree within tolerance.

#### P2 — Rebuild all figure generation from exported tables

- [ ] Implement `F(t)` and `C(t)` directly from completion-period `y` values; assert their final values equal the canonical solution totals.
- [ ] Change Gantt bars to use the actual service duration for each team, not a hard-coded width of 1.
- [ ] Label all time axes in days and all modeled performance axes as network functionality rather than resilience.
- [ ] Use consistent grayscale-safe line styles, markers, and hatch patterns for RRU, ERT, and CIRS.
- [ ] Restore intentional node labels; replace the refactored all-blank `node_labels()` behavior.
- [ ] Plot the expanded underlying shortest-path edges or clearly label direct lines as metric-closure moves.
- [ ] Include depot identity in route legends and preserve arrows/direction.
- [ ] Close figures after saving to avoid accumulating Matplotlib objects in batch workflows.
- [ ] Generate Figs. 3–11 through named script targets with no manual editing or filename copying.

#### P2 — Make scalability evidence depend on the corrected core

- [ ] Keep `run_sensitivity_analysis_scalability.py` in statistics-only mode until the P0 formulation corrections are complete.
- [ ] After core correction, regenerate all size counts because removing orphan `x` variables and adding activation/return constraints will change variables and constraints.
- [ ] Add the core-model/specification version hash to every scalability instance and result row.
- [ ] Run the replicated experiment with an unrestricted Gurobi license and retain all logs before populating manuscript Table 3.
- [ ] Report median runtime, maximum gap, and per-status counts exactly as defined by the driver; do not infer a heuristic threshold from model size alone.

#### P3 — Add parity, formulation, and regression tests

- [ ] Add a golden base-instance test for node order, depots, bridge attributes, all 60 edge times, and all 420 shortest-path times.
- [ ] Add a notebook-migration test documenting the intentional travel-time correction rather than expecting equality with the notebook's missing weights.
- [ ] Test variable/constraint counts by family and verify that no created variable is absent from all constraints and objectives unless intentionally documented.
- [ ] Test objective sense for every CLI and solver workflow.
- [ ] Test earliest starts, due dates, inactive/mandatory teams, subtour elimination, return timing, and horizon completion on license-compatible toy instances.
- [ ] Test status handling for optimal, infeasible, time-limit with incumbent, and time-limit without incumbent cases.
- [ ] Test Pareto deduplication/dominance and epsilon logging on a small deterministic instance.
- [ ] Test each named sensitivity scenario changes only its intended fields.
- [ ] Test Gantt duration, cumulative completion timing, final totals, terminology, and route grouping.
- [ ] Add an end-to-end smoke test that produces a complete evidence directory from a small model.

#### P4 — Clean up naming, interfaces, and reproducibility

- [ ] Rename `resilience` expressions/fields to `final_functionality` while retaining any true resilience metric as a separately defined quantity.
- [ ] Rename or correct `depot_bias`; its present name suggests the opposite probability from its implementation.
- [ ] Replace mutable lists/dictionaries inside frozen configuration dataclasses with immutable or defensively copied structures.
- [ ] Separate model construction, solver configuration, solution extraction, validation, plotting, and CLI orchestration into testable functions with typed inputs/outputs.
- [ ] Record repository commit, dirty-worktree state, Python/package versions, operating system, processor, memory, Gurobi version/license class, and all non-default parameters in every experiment.
- [ ] Prevent accidental output overwrite while ensuring `--overwrite` cannot leave stale logs or instances that appear to belong to a new run.

### A.5 Definition of done before manuscript values are restored

The code revision should not be considered complete until:

1. the authoritative formulation and base instance are versioned;
2. all P0 model corrections are implemented and tested;
3. the base and three named sensitivity cases run through the same solver pipeline;
4. every reported solution has status, incumbent, bound, gap, runtime, log, and canonical solution table;
5. the Pareto frontier is exported with per-subproblem evidence and duplicate/dominance handling;
6. Figs. 3–11 regenerate automatically from exported tables and pass numerical/visual checks;
7. scalability counts are recomputed from the corrected model and actual solves are run with an unrestricted license; and
8. manuscript and response-letter values are updated only from those newly generated artifacts.

## Appendix B. Post-review implementation update (2026-08-06)

The repository now treats the six-city, seed-2 bridge network and its archived
results as **one manuscript presentation case inside a parameterized
implementation**. Network size, seed, planning horizon, graph-generation
ranges, scenario selection, and solver parameters remain command-line inputs.
The refactor deliberately does not force other generated networks to reproduce
the manuscript case.

### B.1 Implemented corrections

- [x] Added `src/bridgesnet/solver.py` as the shared solver path for main,
  sensitivity, Pareto, and scalability runs. Maximum-functionality solves use
  explicit `GRB.MAXIMIZE` and return structured status, incumbent, bound, gap,
  runtime, solution count, and error evidence.
- [x] Added `ObjectiveExpressions.final_functionality` as the common objective
  expression and removed reliance on Gurobi's default model sense.
- [x] Implemented the manuscript earliest-start constraints. The default
  before-presolve count is consequently 3,267 constraints, not the historical
  translated count of 3,177.
- [x] Split depot-origin timing from bridge-origin timing so depot departure no
  longer adds an unexplained bridge service duration.
- [x] Added validation for planning horizon, big-M sign, team dictionaries,
  service times, required bridge attributes, window order, BFI bounds,
  team-specific costs/NewBFI, and finite shortest paths.
- [x] Replaced the unrelated default Cartesian sensitivity sweep with isolated
  constructors for `base`, `service_time_1_2_2`, `due_minus_1`, and
  `initial_bfi_plus_0_10`. All cases copy one generated base network, and the
  BFI case recomputes derived costs and post-intervention BFI.
- [x] Rebuilt solution extraction around a canonical schedule table containing
  bridge, depot, team, route position, start, completion, duration, initial and
  restored BFI, and cost.
- [x] Added completion-period cumulative functionality/cost tables and figures;
  Gantt bars now use actual service durations and time axes are in days.
- [x] Reworked the Pareto driver to retain endpoint evidence, one record and log
  per epsilon subproblem, and a duplicate/dominance-filtered frontier.
- [x] Added JSON/CSV/log provenance outputs and nonzero failure exits to the
  analysis and named-sensitivity runners. The scalability runner uses the same
  solver helper and still preserves per-replication instance snapshots.
- [x] Added overwrite guards and closed generated Matplotlib figures after
  saving.
- [x] Added focused regression tests. The current local result is `11 passed`,
  including a solved license-compatible maximization model.

### B.2 Deliberately preserved formulation choices

The current refactor preserves two choices because changing them would be a
new formulation rather than a correction of the notebook translation:

- every `(depot, team)` pair must depart and return exactly once; inactive teams
  are not yet modeled; and
- routing variables remain defined over the complete node-pair metric closure,
  including the previously identified unused/orphan city-related variables.

These assumptions are now stated in the README. They must also be made explicit
in the manuscript, or changed in a separately versioned formulation with all
model sizes and results regenerated.

### B.3 Essential remaining TODO before manuscript results are claimed

- [ ] Run the base, named sensitivity, Pareto, and replicated scalability
  experiments with an unrestricted Gurobi license and retain all exported logs,
  statuses, incumbents, bounds, gaps, schedules, profiles, and input snapshots.
- [ ] Reconcile the archived sensitivity cost discrepancies from those new
  primary result tables; do not manually carry the old dollar values forward.
- [ ] Regenerate manuscript Figs. 3–11 from the new exports and visually inspect
  the actual PDF figures.
- [ ] Decide whether deployment is mandatory. If teams may be inactive, add and
  test activation variables and regenerate every result and model count.
- [ ] Decide whether to restrict `x` to the intended routing domain; if so,
  rebuild flow constraints, remove orphan variables, and regenerate counts.
- [ ] Add return-time-by-horizon constraints if the manuscript claims that a
  team must physically return before the horizon.
- [ ] Tighten the fixed `M=1000` from valid instance-specific bounds and define
  unassigned start variables more cleanly.
- [ ] Add a lexicographic or secondary cost tie-break for weakly efficient
  Pareto solutions.
- [ ] Add independent post-solve feasibility validation and an end-to-end small
  evidence-directory test.
- [ ] Update the manuscript and response letter only after the corrected,
  solver-supported results replace the archived illustrative values.

### B.4 Handoff note

The repository is being handed off for independent environment and code
validation. The receiving maintainer will add or refresh the Conda environment
definition, create a clean environment from `environment.yml`, and rerun the
test suite and statistics-only sensitivity/scalability checks documented in the
README. This handoff validation is **pending** and should be recorded in the
handoff commit with the resolved package versions, operating system, Gurobi
version/license type, exact commands, and test results. A successful clean-
environment test does not replace the still-required unrestricted-license
optimization runs for the manuscript results.
