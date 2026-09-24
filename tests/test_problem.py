import pytest

from nqueens.problem import board_from_positions, var_id, var_to_position
from nqueens.validators import validate_solution


def test_sat_variable_mapping_is_one_based_and_invertible() -> None:
    assert var_id(4, 0, 0) == 1
    assert var_id(4, 2, 3) == 12
    assert var_to_position(4, 1) == (0, 0)
    assert var_to_position(4, 12) == (2, 3)
    for row in range(5):
        for column in range(5):
            assert var_to_position(5, var_id(5, row, column)) == (row, column)


@pytest.mark.parametrize("args", [(4, 4, 0), (4, -1, 1), (0, 0, 0)])
def test_invalid_variable_mapping_is_rejected(args: tuple[int, int, int]) -> None:
    with pytest.raises(ValueError):
        var_id(*args)


def test_validator_accepts_valid_board() -> None:
    board = board_from_positions(4, [(0, 1), (1, 3), (2, 0), (3, 2)])
    assert validate_solution(board)


@pytest.mark.parametrize(
    "board",
    [
        [[1, 0], [0, 1]],  # diagonal conflict
        [[1, 1], [0, 0]],  # incorrect row and total count
        [[1, 0, 0], [0, 1, 0]],  # not square
        [[1, 0], [0, 2]],  # non-binary value
    ],
)
def test_validator_rejects_invalid_boards(board: list[list[int]]) -> None:
    assert not validate_solution(board)
