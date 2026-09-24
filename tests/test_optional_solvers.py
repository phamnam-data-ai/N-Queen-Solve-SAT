"""Correctness checks that activate only when proprietary runtimes are usable."""

from __future__ import annotations

import pytest

from nqueens.cp.cplex_cp_solver import CplexCPNQueensSolver
from nqueens.mip.cplex_solver import CplexMIPNQueensSolver
from nqueens.mip.gurobi_solver import GurobiNQueensSolver
from nqueens.validators import validate_solution


@pytest.mark.parametrize(
    ("name", "solver_type"),
    [
        ("Gurobi", GurobiNQueensSolver),
        ("CPLEX MIP", CplexMIPNQueensSolver),
        ("CP Optimizer", CplexCPNQueensSolver),
    ],
)
def test_optional_solver_solution_is_valid_when_available(name: str, solver_type: type) -> None:
    solver = solver_type(4, time_limit_sec=20)
    try:
        result = solver.solve()
    finally:
        close = getattr(solver, "close", None)
        if close is not None:
            close()
    if result.status == "SKIPPED":
        pytest.skip(result.error_message)
    assert result.status in {"OPTIMAL", "FEASIBLE"}, result.error_message
    assert result.solution is not None
    assert result.solution_valid is True
    assert validate_solution(result.solution)
