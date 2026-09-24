import pytest

from nqueens.sat.encodings import ENCODING_DETAILS
from nqueens.sat.solver import SATNQueensSolver
from nqueens.validators import validate_solution


@pytest.mark.parametrize("encoding", list(ENCODING_DETAILS))
@pytest.mark.parametrize("n, expected_status", [(1, "SAT"), (2, "UNSAT"), (3, "UNSAT"), (4, "SAT"), (8, "SAT")])
def test_sat_solver_correctness_for_each_encoding(n: int, expected_status: str, encoding: str) -> None:
    solver = SATNQueensSolver(n, encoding=encoding, sat_solver="glucose3")
    try:
        result = solver.solve()
    finally:
        solver.close()
    assert result.status == expected_status, result.error_message
    assert result.num_variables is not None
    assert result.num_clauses is not None
    if expected_status == "SAT":
        assert result.solution is not None
        assert result.solution_valid is True
        assert validate_solution(result.solution)
    else:
        assert result.solution is None


def test_sat_statistics_separate_original_and_auxiliary_variables() -> None:
    solver = SATNQueensSolver(4, encoding="sequential")
    try:
        result = solver.solve()
    finally:
        solver.close()
    assert result.statistics["original_board_variables"] == 16
    assert result.statistics["auxiliary_variables"] > 0
    assert sum(result.statistics["clause_breakdown"].values()) == result.num_clauses
