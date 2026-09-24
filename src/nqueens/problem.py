"""Shared N-Queens representation, variable mapping, and solver result types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

Board = list[list[int]]


def var_id(n: int, row: int, column: int) -> int:
    """Return the one-based SAT variable ID for board cell ``(row, column)``."""
    if n < 1 or not (0 <= row < n and 0 <= column < n):
        raise ValueError(f"invalid cell ({row}, {column}) for N={n}")
    return row * n + column + 1


def var_to_position(n: int, variable: int) -> tuple[int, int]:
    """Invert :func:`var_id` for an original board variable."""
    if n < 1 or not (1 <= variable <= n * n):
        raise ValueError(f"variable {variable} is not a board variable for N={n}")
    zero_based = variable - 1
    return divmod(zero_based, n)


def board_from_positions(n: int, positions: Sequence[tuple[int, int]]) -> Board:
    """Create a zero/one board from queen coordinates."""
    board = [[0 for _ in range(n)] for _ in range(n)]
    for row, column in positions:
        if not (0 <= row < n and 0 <= column < n):
            raise ValueError(f"invalid queen position ({row}, {column}) for N={n}")
        board[row][column] = 1
    return board


def format_board(board: Sequence[Sequence[int]]) -> str:
    """Render a board with ``Q`` for a queen and ``.`` for an empty square."""
    return "\n".join(" ".join("Q" if value else "." for value in row) for row in board)


@dataclass
class NQueensResult:
    """A normalized result returned by every solver adapter."""

    n: int
    method: str
    backend: str
    status: str
    encoding: str | None = None
    build_time_sec: float = 0.0
    solve_time_sec: float = 0.0
    total_time_sec: float = 0.0
    num_variables: int | None = None
    num_clauses: int | None = None
    num_constraints: int | None = None
    solution: Board | None = None
    solution_valid: bool | None = None
    error_message: str | None = None
    statistics: dict[str, Any] = field(default_factory=dict)

    @property
    def build_time(self) -> float:
        """Compatibility alias requested by the assignment brief."""
        return self.build_time_sec

    @property
    def solve_time(self) -> float:
        """Compatibility alias requested by the assignment brief."""
        return self.solve_time_sec

    @property
    def total_time(self) -> float:
        """Compatibility alias requested by the assignment brief."""
        return self.total_time_sec

    @property
    def number_of_variables(self) -> int | None:
        """Human-readable alias for solver/API consumers."""
        return self.num_variables

    @property
    def number_of_clauses(self) -> int | None:
        """Human-readable alias for solver/API consumers."""
        return self.num_clauses

    def to_dict(self, include_solution: bool = False) -> dict[str, Any]:
        """Convert the result to a stable, CSV-friendly dictionary."""
        result = asdict(self)
        if not include_solution:
            result.pop("solution", None)
        # Nested statistics are useful in programmatic use but not a CSV column.
        result.pop("statistics", None)
        result.update(
            {
                "build_time": self.build_time,
                "solve_time": self.solve_time,
                "total_time": self.total_time,
                "number_of_variables": self.number_of_variables,
                "number_of_clauses": self.number_of_clauses,
            }
        )
        return result
