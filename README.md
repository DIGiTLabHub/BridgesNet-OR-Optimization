# BridgesNet OR Optimization

BridgesNet studies how to recover a damaged bridge network when repair capacity is limited, travel takes time, bridge conditions vary, and different intervention teams provide different levels of improvement at different costs. The repository is built for decision support: it turns a bridge-recovery problem into an exact optimization workflow that helps compare resilience gains against operational effort under realistic resource constraints.

The codebase contains two connected workflows:

- a **parameterized synthetic bridge-network workflow** for controlled optimization experiments, Pareto analysis, named manuscript cases, and scalability studies;
- a **Missouri bridge-data workflow** for constructing a directed network from repository-hosted bridge graph and workbook files.

## Why this project matters

Bridge failures and deferred maintenance do not only affect single assets; they disrupt movement across the wider network. In recovery planning, agencies must decide:

- which bridges to service first,
- which depot-team combinations should be dispatched,
- how travel and service timing affect feasible schedules,
- and how much resilience improvement is worth additional cost.

This repository focuses on that decision problem. It emphasizes **operational resilience**, **exact optimization**, and **trade-off analysis** rather than simple ranking rules. The result is a reproducible workflow for exploring how limited crews can be routed to improve network functionality before time windows close.

## Optimization methodology in plain technical terms

At a high level, the synthetic workflow does the following:

1. **Abstract the system as a directed graph.** Cities, depots, and bridge nodes are represented in a network with edge travel times and node-level bridge attributes.
2. **Model heterogeneous repair teams.** Team types (`RRU`, `ERT`, `CIRS`) differ in intervention cost and the amount of bridge functionality they restore.
3. **Respect timing constraints.** Each bridge has an earliest start and due date, each team has a service duration, and route timing is tracked through service-start and completion variables.
4. **Use shortest-path travel times.** Network shortest paths are computed first, then used inside the optimization model to propagate feasible arrival and service times.
5. **Solve an exact MILP.** The resulting formulation is a bridge-recovery version of a **multi-depot vehicle-routing problem with time windows**, implemented as a Gurobi mixed-integer linear program.
6. **Explore trade-offs.** The project supports an evidence-exporting **epsilon-constraint Pareto frontier**, named sensitivity cases, and replicated scalability experiments.

The six-city, seed-2 network and its parameter values are the case used to
present the method in the manuscript. They are **one configuration**, not a
hard-coded definition of the method. The command-line interfaces retain city
count, random seed, planning horizon, graph ranges, scenario selection, and
solver settings as parameters so other controlled network configurations can
be evaluated without rewriting the model.

Use `--depots D` to force `C1` through `CD` to be depots for exact cross-seed
comparisons. If it is omitted, the historical seeded depot-selection rule is
preserved so the default manuscript case remains unchanged.

In the current formulation, one `RRU`, one `ERT`, and one `CIRS` team are
available at every depot, and every depot-team pair is required to depart and
return exactly once. Thus, team deployment is mandatory rather than optional.
The model routes over a complete shortest-path metric closure while retaining
the generated graph as the physical travel network. These choices are kept
explicit because changing either would alter the manuscript formulation and
reported model dimensions.

Core implementation modules live under `src/bridgesnet/`:

- `config.py` — graph and team parameters
- `graph.py` — synthetic network construction
- `paths.py` — shortest-path computation
- `model.py` — Gurobi MILP construction
- `pareto.py` — Pareto frontier generation
- `plots.py` — network, route, gantt, and summary figures
- `results.py` — solution extraction
- `scenarios.py` — isolated named manuscript sensitivity cases
- `solver.py` — shared explicit objective sense, solver settings, and status evidence

## Repository figures

The images below are stored in the repository and render on GitHub through **relative Markdown paths**. Their filenames contain spaces, so the paths are wrapped in angle brackets.

### 1) Abstracted bridge network

![Abstracted bridge network](<ASCE_submission/Figures/Bridges Network.png>)

### 2) Optimized routing result

![Optimized routing result](<ASCE_submission/Figures/Routing Result.png>)

### 3) Cost-resilience Pareto frontier

![Cost-resilience Pareto frontier](<ASCE_submission/Figures/Pareto Frontier.png>)

### 4) Service schedule variation

![Service schedule variation](<ASCE_submission/Figures/Gantt Chart of Service Variation.png>)

## Environment setup

The repository ships with a Conda environment definition in `environment.yml`.

```bash
conda env create -f environment.yml
conda activate bridgesnet
```

The environment includes:

- Python 3.11
- Gurobi
- `networkx`
- `matplotlib`
- `numpy`
- `pytest`

### Handoff environment validation

As part of the repository handoff, the Conda environment definition will be
added or refreshed by the receiving maintainer and the code will be tested in
that newly created environment. This independent environment validation is
still pending; the current results were obtained from the existing local
`bridgesnet` environment.

The handoff check should run:

```bash
conda env create -f environment.yml
conda run -n bridgesnet python scripts/run_tests.py
conda run -n bridgesnet python scripts/run_sensitivity_analysis.py \
  --model-stats-only --output-dir results/handoff-sensitivity-check
conda run -n bridgesnet python scripts/run_sensitivity_analysis_scalability.py \
  --model-stats-only --replications 1 \
  --output-dir results/handoff-scalability-check
```

Record the operating system, package versions, Gurobi version/license type,
test result, and any environment-file changes in the handoff commit. Full
optimization remains dependent on an adequate Gurobi license.

## Gurobi license setup

The optimization scripts require a valid Gurobi license.

If your license file is already installed in a standard location, Gurobi will usually detect it automatically. Otherwise, set the license path explicitly before running optimization scripts:

```bash
export GRB_LICENSE_FILE=/path/to/gurobi.lic
```

If you are setting up a new machine, obtain and install a license through Gurobi first, then confirm that your environment can import `gurobipy`.

## Running the workflows

Run commands from the repository root.

### Visualize the synthetic bridge network

Use this script to generate the synthetic graph and print basic network statistics, including the total shortest-path travel distance.

```bash
python scripts/visualize_graph.py --cities 6 --seed 2 --output results/network.pdf
```

Optional interactive display:

```bash
python scripts/visualize_graph.py --cities 6 --seed 2 --output results/network.pdf --show
```

Key outputs:

- `results/network.pdf`
- console summary of bridge count, city count, and total shortest-path distance

### Run the core optimization analysis

This is the main end-to-end experiment: generate one configured graph, compute
shortest paths, explicitly maximize final network functionality, and export
both manuscript figures and machine-readable solver evidence.

```bash
python scripts/run_analysis.py \
  --cities 6 --seed 2 --planning-horizon 8 \
  --output-dir results/analysis --pareto
```

If you also want the LP written to disk:

```bash
python scripts/run_analysis.py \
  --cities 6 --seed 2 --planning-horizon 8 \
  --time-limit 3600 --mip-gap 0.0001 --threads 10 \
  --output-dir results/analysis --pareto --write-lp
```

Key outputs in `results/analysis/`:

- `network.png` and `network.pdf`
- `routes.png` and `routes.pdf`
- `gantt.png` and `gantt.pdf`
- `cumulative_profile.png`, `cumulative_profile.pdf`, and `cumulative_profile.csv`
- `instance.json`, `model_statistics.json`, and `solve_record.json`
- `solution_summary.json` and `solution_schedule.csv`
- `gurobi_primary.log`
- `pareto.png` and `pareto.pdf` when `--pareto` is used
- `pareto_subproblems.csv`, filtered `pareto_points.csv`, `pareto_endpoints.json`, and `pareto_logs/`
- `bridge.lp` when `--write-lp` is used

The process exits nonzero if no incumbent is available. A time-limited incumbent
is still exported with its bound and final gap; it is not mislabeled as optimal.

### Run the named manuscript sensitivity cases

This driver creates the base graph once and applies each sensitivity change to
a copy. Consequently, changes in results are attributable to the named
parameter rather than to regeneration of the random network. The four default
cases are the base case, service durations `(1,2,2)`, all due dates minus one
day, and all initial BFI values plus `0.10` (with derived cost and post-service
BFI recomputed).

Run the manuscript configuration:

```bash
python scripts/run_sensitivity_analysis.py \
  --cities 6 --seed 2 --planning-horizon 8 \
  --output-dir results/sensitivity
```

Run selected cases on another parameterized configuration:

```bash
python scripts/run_sensitivity_analysis.py \
  --cities 7 --seed 14 --planning-horizon 10 \
  --depots 2 \
  --bridge-count-range 1:2 --bfi-range 0.15:0.45 \
  --start-range 0:3 --due-offset-range 2:6 \
  --scenarios base,due_minus_1 \
  --output-dir results/sensitivity-custom
```

To validate all instances and counts without solving:

```bash
python scripts/run_sensitivity_analysis.py \
  --model-stats-only --output-dir results/sensitivity-stats
```

Key outputs in `results/sensitivity/`:

- `sensitivity_results.csv`
- `experiment_metadata.json`
- one folder per scenario containing `scenario_input.json`, `solve_record.json`,
  the Gurobi log, schedule/profile CSVs, and duration-aware figures

### Run the replicated scalability experiment

The scalability driver creates exact 15-, 30-, 45-, and 60-bridge synthetic
instances, runs replicated maximum-functionality MILPs, and records the model
sizes, solver logs, instances, runtimes, bounds, and optimality gaps.

```bash
python scripts/run_sensitivity_analysis_scalability.py
```

The default protocol uses 10 replications per size, a one-hour limit per solve,
10 Gurobi threads, and a relative MIP gap target of `1e-4`. Each runtime covers
one maximum-final-functionality problem, not the complete Pareto procedure.
It uses the same shared solver path and explicit `GRB.MAXIMIZE` objective as the
main and named-sensitivity drivers.

To verify instance generation and model sizes without optimizing:

```bash
python scripts/run_sensitivity_analysis_scalability.py \
  --model-stats-only --replications 1 \
  --output-dir results/scalability-stats
```

Key outputs include:

- `scalability_runs.csv` — one row per replication
- `scalability_summary.csv` and `scalability_table.md` — aggregate results
- `experiment_metadata.json` — protocol, versions, seeds, and solver settings
- `instances/` — complete generated input snapshots with SHA-256 identifiers
- `logs/` — one Gurobi log per attempted solve

### Create a Missouri bridge network from repository data

This workflow uses local repository data files:

- `Missouri-Bridges-Data-Graphs/missouri_bridge_graph.pkl`
- `Missouri-Bridges-Data-Graphs/MOpoorbridges.xlsx`

The script is **interactive**. It prompts for 1-2 counties and then for 1-4 depot definitions, including optional name and coordinate overrides.

Run with default inputs and outputs:

```bash
python scripts/create_MO_bridge_network.py
```

Write custom outputs:

```bash
python scripts/create_MO_bridge_network.py --output-graph results/mo_network_custom.pkl --output-plot results/mo_network_custom.pdf
```

Show the generated plot in an interactive window:

```bash
python scripts/create_MO_bridge_network.py --show
```

Default outputs:

- `results/mo_bridge_network.pkl`
- `results/mo_bridge_network.pdf`

### Run the test suite

```bash
python scripts/run_tests.py
```

This wrapper runs:

```bash
python -m pytest tests
```

The tests include a small Gurobi optimization that fits a restricted license,
plus regression checks for objective sense, earliest-start enforcement,
scenario isolation, model dimensions, Pareto evidence, cumulative outputs, and
service-duration plotting. The default manuscript model before presolve contains
3,240 binary variables, 90 continuous variables, and 3,267 constraints. The
constraint count is 90 larger than the historical notebook translation because
the manuscript earliest-start equation is now implemented.

## Project structure

- `scripts/` — runnable entry points for visualization, optimization, sensitivity, Missouri data processing, and tests
- `src/bridgesnet/` — reusable modeling and plotting modules
- `tests/` — automated tests
- `Bridge_Sensitivity.ipynb` — original notebook workflow that this repository modularizes

## What this README does and does not claim

This repository provides a reproducible optimization and analysis workflow for bridge-network recovery planning. It demonstrates graph-based modeling, team heterogeneity, route-and-time feasibility, Pareto trade-offs, and parameter sensitivity. Historical manuscript figures and numbers are illustrative until regenerated with the corrected runners and retained solver records. The repository does **not** claim field deployment or external validation beyond the scripts, datasets, and outputs present here.
