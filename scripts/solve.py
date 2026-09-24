"""Solve one N-Queens instance from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nqueens.problem import format_board


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solve N-Queens with SAT, CP-SAT, or an optional commercial solver.")
    parser.add_argument("--method", choices=["sat", "cpsat", "gurobi", "cplex-mip", "cplex-cp"], default="sat")
    parser.add_argument("--n", type=int, required=True, help="board size (N >= 1)")
    parser.add_argument("--encoding", choices=["pairwise", "sequential", "binary", "commander", "product"], default="sequential")
    parser.add_argument("--sat-solver", default="glucose3", help="PySAT backend, e.g. glucose3, glucose4, minisat22")
    parser.add_argument("--time-limit", type=float, default=None, help="optional time limit for non-SAT adapters")
    parser.add_argument("--commander-group-size", type=int, default=3)
    parser.add_argument("--product-dimension", type=int, default=None)
    parser.add_argument("--show-board", action="store_true")
    parser.add_argument("--show-statistics", action="store_true")
    return parser


def make_solver(arguments: argparse.Namespace):
    if arguments.method == "sat":
        from nqueens.sat.solver import SATNQueensSolver

        return SATNQueensSolver(
            arguments.n, arguments.encoding, arguments.sat_solver,
            commander_group_size=arguments.commander_group_size,
            product_dimension=arguments.product_dimension,
        )
    if arguments.method == "cpsat":
        from nqueens.cpsat.solver import CPSATNQueensSolver

        return CPSATNQueensSolver(arguments.n, time_limit_sec=arguments.time_limit)
    if arguments.method == "gurobi":
        from nqueens.mip.gurobi_solver import GurobiNQueensSolver

        return GurobiNQueensSolver(arguments.n, time_limit_sec=arguments.time_limit)
    if arguments.method == "cplex-mip":
        from nqueens.mip.cplex_solver import CplexMIPNQueensSolver

        return CplexMIPNQueensSolver(arguments.n, time_limit_sec=arguments.time_limit)
    from nqueens.cp.cplex_cp_solver import CplexCPNQueensSolver

    return CplexCPNQueensSolver(arguments.n, time_limit_sec=arguments.time_limit)


def main() -> int:
    arguments = build_parser().parse_args()
    solver = make_solver(arguments)
    try:
        result = solver.solve()
    finally:
        close = getattr(solver, "close", None)
        if close is not None:
            close()
    # A single-instance CLI is intended for inspection, so include the board;
    # benchmark CSV serialization deliberately omits this nested field.
    print(json.dumps(result.to_dict(include_solution=True), indent=2, default=str))
    if arguments.show_statistics and result.statistics:
        print("\nSAT statistics:")
        print(json.dumps(result.statistics, indent=2, default=str))
    if arguments.show_board and result.solution is not None:
        print("\nBoard:")
        print(format_board(result.solution))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
