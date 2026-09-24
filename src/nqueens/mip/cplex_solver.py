"""Optional IBM CPLEX MIP formulation through DOcplex."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from ..problem import NQueensResult, board_from_positions
from ..validators import validate_solution
from .gurobi_solver import _likely_license_failure


class CplexMIPNQueensSolver:
    """Binary N-Queens MIP, returning SKIPPED if CPLEX is unavailable."""

    def __init__(self, n: int, *, time_limit_sec: float | None = None) -> None:
        if n < 1:
            raise ValueError("N must be at least 1")
        self.n = n
        self.time_limit_sec = time_limit_sec
        self._model: Any | None = None
        self._x: dict[tuple[int, int], Any] = {}
        self._build_time_sec = 0.0
        self._num_constraints: int | None = None

    def build(self) -> None:
        started = perf_counter()
        from docplex.mp.model import Model

        model = Model(name="nqueens")
        if self.time_limit_sec is not None:
            model.parameters.timelimit = self.time_limit_sec
        x = {(row, column): model.binary_var(name=f"x_{row}_{column}") for row in range(self.n) for column in range(self.n)}
        for row in range(self.n):
            model.add_constraint(model.sum(x[row, column] for column in range(self.n)) == 1, ctname=f"row_{row}")
        for column in range(self.n):
            model.add_constraint(model.sum(x[row, column] for row in range(self.n)) == 1, ctname=f"column_{column}")
        for delta in range(-(self.n - 1), self.n):
            cells = [(row, row - delta) for row in range(self.n) if 0 <= row - delta < self.n]
            if len(cells) > 1:
                model.add_constraint(model.sum(x[cell] for cell in cells) <= 1, ctname=f"main_{delta}")
        for total in range(1, 2 * self.n - 2):
            cells = [(row, total - row) for row in range(self.n) if 0 <= total - row < self.n]
            if len(cells) > 1:
                model.add_constraint(model.sum(x[cell] for cell in cells) <= 1, ctname=f"anti_{total}")
        model.minimize(0)
        self._model, self._x = model, x
        self._num_constraints = model.number_of_constraints
        self._build_time_sec = perf_counter() - started

    def solve(self) -> NQueensResult:
        total_started = perf_counter()
        try:
            if self._model is None:
                self.build()
        except ModuleNotFoundError as error:
            return NQueensResult(self.n, "cplex-mip", "cplex-mip", "SKIPPED", total_time_sec=perf_counter() - total_started,
                                 error_message=f"DOcplex/CPLEX is not installed: {error}")
        except Exception as error:
            status = "SKIPPED" if _likely_license_failure(error) else "ERROR"
            return NQueensResult(self.n, "cplex-mip", "cplex-mip", status, total_time_sec=perf_counter() - total_started,
                                 error_message=f"CPLEX unavailable: {error}")

        assert self._model is not None
        started = perf_counter()
        try:
            solution = self._model.solve(log_output=False)
            solve_time = perf_counter() - started
            if solution is not None:
                board = board_from_positions(
                    self.n,
                    [(row, column) for (row, column), variable in self._x.items() if solution.get_value(variable) > 0.5],
                )
                valid = validate_solution(board)
                status = "OPTIMAL" if valid else "ERROR"
                error = None if valid else "CPLEX returned a solution that failed independent validation"
            else:
                board, valid = None, None
                detail = str(self._model.solve_details.status).lower()
                status = "TIMEOUT" if "time" in detail else ("UNSAT" if "infeasible" in detail else "ERROR")
                error = None if status != "ERROR" else f"CPLEX solve status: {self._model.solve_details.status}"
            return NQueensResult(
                self.n, "cplex-mip", "cplex-mip", status, build_time_sec=self._build_time_sec,
                solve_time_sec=solve_time, total_time_sec=self._build_time_sec + solve_time,
                num_variables=self.n * self.n, num_constraints=self._num_constraints,
                solution=board, solution_valid=valid, error_message=error,
            )
        except Exception as error:
            solve_time = perf_counter() - started
            status = "SKIPPED" if _likely_license_failure(error) else "ERROR"
            return NQueensResult(self.n, "cplex-mip", "cplex-mip", status, build_time_sec=self._build_time_sec,
                                 solve_time_sec=solve_time, total_time_sec=self._build_time_sec + solve_time,
                                 num_variables=self.n * self.n, num_constraints=self._num_constraints,
                                 error_message=str(error))
