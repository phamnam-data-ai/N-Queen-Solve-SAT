"""Independent solution checks shared by all solving approaches."""

from __future__ import annotations

from collections.abc import Sequence


def validate_solution(board: Sequence[Sequence[int | bool]]) -> bool:
    """Return whether ``board`` is a complete, valid N-Queens placement.

    This deliberately does not trust any solver-specific data structure.  A
    valid board must be square, contain exactly one queen in each row and
    column, and have no diagonal conflicts.
    """
    n = len(board)
    if n < 1 or any(len(row) != n for row in board):
        return False

    positions: list[tuple[int, int]] = []
    for row_index, row in enumerate(board):
        for column_index, value in enumerate(row):
            if value not in (0, 1, False, True):
                return False
            if bool(value):
                positions.append((row_index, column_index))

    if len(positions) != n:
        return False
    if any(sum(bool(value) for value in row) != 1 for row in board):
        return False

    columns = [column for _, column in positions]
    if len(set(columns)) != n:
        return False
    main_diagonals = [row - column for row, column in positions]
    anti_diagonals = [row + column for row, column in positions]
    return len(set(main_diagonals)) == n and len(set(anti_diagonals)) == n
