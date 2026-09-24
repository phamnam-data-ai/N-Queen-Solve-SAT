"""N-Queens model using the compact CP-SAT integer formulation."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from ..problem import NQueensResult, board_from_positions
from ..validators import validate_solution


class CPSATNQueensSolver:
    """Solve N-Queens with AllDifferent on columns and both diagonal forms."""

    def __init__(self, n: int, *, time_limit_sec: float | None = None) -> None:
        if n < 1:
            raise ValueError("N must be at least 1")
        self.n = n
        self.time_limit_sec = time_limit_sec
        self._model: Any | None = None
        self._queens: list[Any] = []
        self._cp_model: Any | None = None
        self._build_time_sec = 0.0
        self._num_constraints: int | None = None

    def build(self) -> None:
        """Build the integer ``queen[row] = column`` CP-SAT formulation."""
        started = perf_counter()
        from ortools.sat.python import cp_model

        model = cp_model.CpModel()
        queens = [model.new_int_var(0, self.n - 1, f"queen_{row}") for row in range(self.n)]
        model.add_all_different(queens)
        model.add_all_different([queens[row] + row for row in range(self.n)])
        model.add_all_different([queens[row] - row for row in range(self.n)])
        self._model = model
        self._queens = queens
        self._cp_model = cp_model
        self._num_constraints = 3
        self._build_time_sec = perf_counter() - started

    def solve(self) -> NQueensResult:
        """Execute CP-SAT and validate every feasible solution."""
        total_started = perf_counter()
        try:
            if self._model is None:
                self.build()
        except ModuleNotFoundError as error:
            return NQueensResult(
                n=self.n,
                method="cpsat",
                backend="ortools-cp-sat",
                status="SKIPPED",
                total_time_sec=perf_counter() - total_started,
                error_message=f"OR-Tools is not installed: {error}",
            )
        except Exception as error:
            return NQueensResult(
                n=self.n,
                method="cpsat",
                backend="ortools-cp-sat",
                status="ERROR",
                total_time_sec=perf_counter() - total_started,
                error_message=str(error),
            )

        assert self._cp_model is not None and self._model is not None
        solver = self._cp_model.CpSolver()
        if self.time_limit_sec is not None:
            solver.parameters.max_time_in_seconds = self.time_limit_sec
        solve_started = perf_counter()
        try:
            code = solver.solve(self._model)
            solve_time = perf_counter() - solve_started
            name = solver.status_name(code).upper()
            feasible_codes = {self._cp_model.OPTIMAL, self._cp_model.FEASIBLE}
            if code in feasible_codes:
                positions = [(row, int(solver.value(variable))) for row, variable in enumerate(self._queens)]
                board = board_from_positions(self.n, positions)
                valid = validate_solution(board)
                status = name if valid else "ERROR"
                error = None if valid else "CP-SAT returned a solution that failed independent validation"
            else:
                board = None
                valid = None
                error = None
                if name == "UNKNOWN" and self.time_limit_sec is not None:
                    status = "TIMEOUT"
                elif name == "INFEASIBLE":
                    status = "UNSAT"
                else:
                    status = name
            return NQueensResult(
                n=self.n,
                method="cpsat",
                backend="ortools-cp-sat",
                status=status,
                build_time_sec=self._build_time_sec,
                solve_time_sec=solve_time,
                total_time_sec=self._build_time_sec + solve_time,
                num_variables=self.n,
                num_constraints=self._num_constraints,
                solution=board,
                solution_valid=valid,
                error_message=error,
            )
        except Exception as error:
            solve_time = perf_counter() - solve_started
            return NQueensResult(
                n=self.n,
                method="cpsat",
                backend="ortools-cp-sat",
                status="ERROR",
                build_time_sec=self._build_time_sec,
                solve_time_sec=solve_time,
                total_time_sec=self._build_time_sec + solve_time,
                num_variables=self.n,
                num_constraints=self._num_constraints,
                error_message=str(error),
            )
