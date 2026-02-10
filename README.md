# BridgesNet OR Optimization

This project modularizes the `Bridge_Sensitivity.ipynb` workflow into reusable
Python modules and scripts for reproducible experiments, figures, and testing.

## Requirements (from the original notebook)

- Python 3.11
- Dependencies: `networkx`, `matplotlib`, `numpy`, `gurobipy`
- A valid Gurobi license file (`gurobi.lic`) or `GRB_LICENSE_FILE` environment variable

The model generates a directed bridge network with synthetic attributes, then
optimizes dispatching repair teams to maximize resilience subject to time windows
and routing constraints.

## Running Steps

1. Create and activate the conda environment:

```bash
conda env create -f environment.yml
conda activate bridgesnet
```

2. Make sure a Gurobi license is available:

```bash
export GRB_LICENSE_FILE=/path/to/gurobi.lic
```

3. (Optional) Visualize the generated network:

```bash
python scripts/visualize_graph.py --output results/network.pdf
```

## Project Layout

- `src/bridgesnet/`: reusable modules (graph generation, model, plots)
- `scripts/`: execution entrypoints
- `tests/`: unit tests
- `Bridge_Sensitivity.ipynb`: original notebook

## Run the Analysis (single run)

```bash
python scripts/run_analysis.py --pareto --output-dir results
```

Options:
- `--cities <int>`: number of cities (default: 6)
- `--seed <int>`: random seed (default: 2)
- `--planning-horizon <int>`: planning horizon (default: 8)
- `--output-dir <path>`: output folder (default: `results`)
- `--pareto`: generate Pareto frontier figure
- `--write-lp`: write `bridge.lp` to the output folder

Outputs:
- `results/network.(png|pdf)`
- `results/routes.(png|pdf)`
- `results/gantt.(png|pdf)`
- `results/pareto.(png|pdf)` (when `--pareto` is used)

## Run Sensitivity Analysis (parametric sweep)

```bash
python scripts/run_sensitivity_analysis.py
```

Options:
- `--cities <int>`: number of cities (default: 6)
- `--output-dir <path>`: output folder (default: `results/sensitivity`)
- `--alpha <list>`: comma-separated values (default: `0.3,0.5,0.7`)
- `--planning-horizon <list>`: comma-separated values (default: `6,8,10`)
- `--depot-bias <list>`: comma-separated values (default: `0.7,0.9`)
- `--bridge-bfi-range <list>`: comma-separated `low:high` pairs (default: `0.1:0.3,0.2:0.4`)
- `--base-cost-scale <list>`: comma-separated values (default: `0.8,1.0,1.2`)
- `--delta-functionality-scale <list>`: comma-separated values (default: `0.8,1.0,1.2`)
- `--seed <list>`: comma-separated values (default: `1,2,3`)

Outputs:
- `results/sensitivity/sensitivity_results.csv`
- summary plots in `results/sensitivity/summary_*.(png|pdf)`
- boxplots in `results/sensitivity/box_*.(png|pdf)`
- histograms in `results/sensitivity/hist_*.(png|pdf)`

Override sweep ranges with comma-separated lists:

```bash
python scripts/run_sensitivity_analysis.py \
  --alpha 0.2,0.4,0.6 \
  --planning-horizon 6,8,10 \
  --depot-bias 0.6,0.8 \
  --bridge-bfi-range 0.1:0.3,0.2:0.4 \
  --base-cost-scale 0.9,1.0,1.1 \
  --delta-functionality-scale 0.9,1.0,1.1 \
  --seed 1,2
```

## Run Tests

```bash
python scripts/run_tests.py
```

## Visualize the Bridge Network

```bash
python scripts/visualize_graph.py --output results/network.pdf
```

Options:
- `--cities <int>`: number of cities (default: 6)
- `--seed <int>`: random seed (default: 2)
- `--output <path>`: output PDF path (default: `results/network.pdf`)

## Notes on the Model

- The objective maximizes post-intervention resilience.
- Each depot-team pair departs and returns exactly once.
- Time windows are enforced using a big-M formulation.
- Shortest-path travel times are used in scheduling constraints.
