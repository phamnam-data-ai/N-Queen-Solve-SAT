import pytest

pytest.importorskip("ortools")

from nqueens.cpsat.solver import CPSATNQueensSolver
from nqueens.validators import validate_solution


@pytest.mark.parametrize("n", [4, 8])
def test_cpsat_returns_valid_nqueens_solution(n: int) -> None:
    result = CPSATNQueensSolver(n).solve()
    assert result.status in {"OPTIMAL", "FEASIBLE"}, result.error_message
    assert result.solution is not None
    assert result.solution_valid is True
    assert validate_solution(result.solution)
