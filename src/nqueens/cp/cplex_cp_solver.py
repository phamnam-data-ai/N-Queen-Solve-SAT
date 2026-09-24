"""Optional N-Queens formulation for IBM CP Optimizer (DOcplex CP)."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from ..mip.gurobi_solver import _likely_license_failure
from ..problem import NQueensResult, board_from_positions
from ..validators import validate_solution


class CplexCPNQueensSolver:
    """AllDifferent CP model, safely skipped without CP Optimizer."""

    def __init__(self, n: int, *, time_limit_sec: float | None = None) -> None:
        if n < 1:
            raise ValueError("N must be at least 1")
        self.n = n
        self.time_limit_sec = time_limit_sec
        self._model: Any | None = None
        self._queens: list[Any] = []
        self._build_time_sec = 0.0

    def build(self) -> None:
        started = perf_counter()
        from docplex.cp.model import CpoModel, all_diff, integer_var

        model = CpoModel(name="nqueens")
        queens = [integer_var(min=0, max=self.n - 1, name=f"queen_{row}") for row in range(self.n)]
        model.add(all_diff(queens))
        model.add(all_diff([queens[row] + row for row in range(self.n)]))
        model.add(all_diff([queens[row] - row for row in range(self.n)]))
        self._model, self._queens = model, queens
        self._build_time_sec = perf_counter() - started

    def solve(self) -> NQueensResult:
        total_started = perf_counter()
        try:
            if self._model is None:
                self.build()
        except ModuleNotFoundError as error:
            return NQueensResult(self.n, "cplex-cp", "cplex-cp", "SKIPPED", total_time_sec=perf_counter() - total_started,
                                 error_message=f"DOcplex CP/CP Optimizer is not installed: {error}")
        except Exception as error:
            status = "SKIPPED" if _likely_license_failure(error) else "ERROR"
            return NQueensResult(self.n, "cplex-cp", "cplex-cp", status, total_time_sec=perf_counter() - total_started,
                                 error_message=f"CP Optimizer unavailable: {error}")

        assert self._model is not None
        started = perf_counter()
        try:
            options: dict[str, Any] = {"LogVerbosity": "Quiet"}
            if self.time_limit_sec is not None:
                options["TimeLimit"] = self.time_limit_sec
            result = self._model.solve(**options)
            solve_time = perf_counter() - started
            status_text = str(result.get_solve_status()).upper()
            if "FEASIBLE" in status_text or "OPTIMAL" in status_text:
                board = board_from_positions(self.n, [(row, int(result.get_value(variable))) for row, variable in enumerate(self._queens)])
                valid = validate_solution(board)
                status = "OPTIMAL" if "OPTIMAL" in status_text and valid else ("FEASIBLE" if valid else "ERROR")
                error = None if valid else "CP Optimizer returned a solution that failed independent validation"
            else:
                board, valid = None, None
                status = "TIMEOUT" if "UNKNOWN" in status_text and self.time_limit_sec is not None else (
                    "UNSAT" if "INFEASIBLE" in status_text else "ERROR"
                )
                error = None if status != "ERROR" else f"CP Optimizer solve status: {status_text}"
            return NQueensResult(
                self.n, "cplex-cp", "cplex-cp", status, build_time_sec=self._build_time_sec,
                solve_time_sec=solve_time, total_time_sec=self._build_time_sec + solve_time,
                num_variables=self.n, num_constraints=3, solution=board,
                solution_valid=valid, error_message=error,
            )
        except Exception as error:
            solve_time = perf_counter() - started
            status = "SKIPPED" if _likely_license_failure(error) else "ERROR"
            return NQueensResult(self.n, "cplex-cp", "cplex-cp", status, build_time_sec=self._build_time_sec,
                                 solve_time_sec=solve_time, total_time_sec=self._build_time_sec + solve_time,
                                 num_variables=self.n, num_constraints=3, error_message=str(error))
