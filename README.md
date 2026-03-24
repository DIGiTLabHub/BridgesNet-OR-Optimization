# BridgesNet OR Optimization

BridgesNet studies how to recover a damaged bridge network when repair capacity is limited, travel takes time, bridge conditions vary, and different intervention teams provide different levels of improvement at different costs. The repository is built for decision support: it turns a bridge-recovery problem into an exact optimization workflow that helps compare resilience gains against operational effort under realistic resource constraints.

The codebase contains two connected workflows:

- a **synthetic bridge-network workflow** for controlled optimization experiments, Pareto analysis, and sensitivity studies;
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
3. **Respect timing constraints.** Each bridge has a service window, each team has service time, and route timing is tracked through service-start variables and time-window constraints.
4. **Use shortest-path travel times.** Network shortest paths are computed first, then used inside the optimization model to propagate feasible arrival and service times.
5. **Solve an exact MILP.** The resulting formulation is a bridge-recovery version of a **multi-depot vehicle-routing problem with time windows**, implemented as a Gurobi mixed-integer linear program.
6. **Explore trade-offs.** The project supports **Pareto frontier generation** using an epsilon-constraint approach and broader **sensitivity analysis** over planning and cost/functionality parameters.

Core implementation modules live under `src/bridgesnet/`:

- `config.py` — graph and team parameters
- `graph.py` — synthetic network construction
- `paths.py` — shortest-path computation
- `model.py` — Gurobi MILP construction
- `pareto.py` — Pareto frontier generation
- `plots.py` — network, route, gantt, and summary figures
- `results.py` — solution extraction

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

This is the main end-to-end synthetic experiment: build the graph, compute shortest paths, solve the Gurobi model, and save the network, routes, gantt chart, and optional Pareto figure.

```bash
python scripts/run_analysis.py --cities 6 --seed 2 --planning-horizon 8 --output-dir results --pareto
```

If you also want the LP written to disk:

```bash
python scripts/run_analysis.py --cities 6 --seed 2 --planning-horizon 8 --output-dir results --pareto --write-lp
```

Key outputs in `results/`:

- `network.png` and `network.pdf`
- `routes.png` and `routes.pdf`
- `gantt.png` and `gantt.pdf`
- `pareto.png` and `pareto.pdf` when `--pareto` is used
- `bridge.lp` when `--write-lp` is used

The script also prints the solved objective, cost, resilience, and visited-bridge count.

### Run sensitivity analysis sweeps

Use this script to sweep parameter combinations and summarize how resilience and cost respond to planning assumptions.

Default sweep:

```bash
python scripts/run_sensitivity_analysis.py
```

Example custom sweep:

```bash
python scripts/run_sensitivity_analysis.py --output-dir results/sensitivity --cities 6 --alpha 0.2,0.4,0.6 --planning-horizon 6,8,10 --depot-bias 0.6,0.8 --bridge-bfi-range 0.1:0.3,0.2:0.4 --base-cost-scale 0.9,1.0,1.1 --delta-functionality-scale 0.9,1.0,1.1 --seed 1,2
```

Key outputs in `results/sensitivity/`:

- `sensitivity_results.csv`
- `summary_*.(png|pdf)` plots
- `box_*.(png|pdf)` plots
- `hist_*.(png|pdf)` plots

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

## Project structure

- `scripts/` — runnable entry points for visualization, optimization, sensitivity, Missouri data processing, and tests
- `src/bridgesnet/` — reusable modeling and plotting modules
- `tests/` — automated tests
- `Bridge_Sensitivity.ipynb` — original notebook workflow that this repository modularizes

## What this README does and does not claim

This repository provides a reproducible optimization and analysis workflow for bridge-network recovery planning. It demonstrates graph-based modeling, team heterogeneity, route-and-time feasibility, Pareto trade-offs, and parameter sensitivity. It does **not** claim field deployment or external validation beyond the scripts, datasets, and outputs present in this repository.
