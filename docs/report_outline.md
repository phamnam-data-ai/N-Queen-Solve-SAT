# SAT Encoding for the N-Queens Problem: An Experimental Comparison with Exact Solving Methods

> Template only: no experimental values are fabricated. Generate `results/environment.json` by running the benchmark, then complete its cited fields.

## Abstract

Draft: This work compares N-Queens SAT cardinality encodings and exact CP/MIP formulations, separating model-construction from solve time. Add only measured findings after experiments.

## 1. Introduction

- N-Queens, constraint satisfaction, SAT solving, and experimental motivation.
- Objective: compare model size and measured performance without presupposing a winner.

## 2. Background

- N-Queens; SAT/CNF; ALO, AMO, and exactly-one; exact solving approaches.

## 3. Problem Formulation

Define `x[r,c]`, row/column exactly-one, diagonal AMO, and `v(r,c)=rN+c+1`.

## 4. SAT Encodings

Pairwise, sequential, binary, commander, and product. Use [`methodology.md`](methodology.md) to distinguish PySAT wrappers from custom CNF code.

## 5. Alternative Exact Methods

CP-SAT, Gurobi MIP, CPLEX MIP, and CP Optimizer; identify which optional methods were actually available.

## 6. Experimental Setup

The following values are automatically captured by `results/environment.json`:

| Item | Source |
| --- | --- |
| Hardware / OS / Python | environment root fields |
| Package versions | `package_versions` |
| N values | `benchmark_configuration.n_values` |
| Repetitions | `benchmark_configuration.repeats` |
| Timeout per experiment | `benchmark_configuration.timeout_sec` |
| SAT backend and parameters | `benchmark_configuration` |

<!-- BEGIN AUTO ENVIRONMENT -->
| Item | Measured configuration |
| --- | --- |
| OS / Python | Windows-11-10.0.26100-SP0 / 3.13.9 |
| CPU / RAM | Intel64 Family 6 Model 186 Stepping 3, GenuineIntel / 34029125632 bytes |
| Packages | python-sat=1.9.dev15, ortools=unavailable, numpy=2.5.3, pandas=3.0.6, matplotlib=unavailable, psutil=7.2.2, gurobipy=unavailable, docplex=unavailable, cplex=unavailable |
| N values | [150, 200, 300, 500] |
| Repetitions | 1 |
| Timeout per experiment | 60.0 s |
| Methods / SAT backend | ['sat'] / glucose3 |
| SAT parameters | encodings=['pairwise', 'sequential', 'binary', 'commander', 'product']; commander group=3; product dimension=None |
<!-- END AUTO ENVIRONMENT -->

Explain that warm-up is excluded, every run has a subprocess wall timeout, and aggregates include only independently validated solutions.

## 7. Experimental Results

Populate from `results/summary_results.csv`; do not make up entries.

| Method | Encoding / backend | N | Mean solve time | Median solve time | Mean total time | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| _fill from summary CSV_ |  |  |  |  |  |  |

Insert available figures: `solve_time_comparison.png`, `solve_time_log.png`, `total_time_comparison.png`, `sat_encoding_time.png`, `sat_encoding_by_n.png`, `sat_clause_count.png`, and `sat_variable_count.png`.

## 8. Discussion

- Which encoding made the fewest clauses/variables?
- Which solved fastest at each N, and how did build cost differ?
- How did SAT, CP-SAT, and MIP scale under the same timeout?
- Did auxiliaries show a size-versus-propagation trade-off?

## 9. Threats to Validity

Hardware dependence, package/solver versions, heuristics, proprietary licenses, timeout bias, repeat variance, and memory pressure.

## 10. Conclusion

Summarize measured trends only; do not generalize beyond configurations and N values actually tested.
