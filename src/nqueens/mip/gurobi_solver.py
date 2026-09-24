"""Optional Gurobi binary MIP formulation for N-Queens."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from ..problem import NQueensResult, board_from_positions
from ..validators import validate_solution


def _likely_license_failure(error: Exception) -> bool:
    text = str(error).lower()
    # DOcplex reports absent proprietary runtimes with different wording from
    # license failures.  All of these are environmental availability states,
    # not modeling failures, and must not abort the benchmark.
    return any(
        token in text
        for token in (
            "license", "licence", "expired", "not licensed", "unable to open",
            "cplex runtime", "cannot solve model", "cpoptimizer", "executable file",
            "no cplex", "failed to connect to gurobi",
        )
    )


class GurobiNQueensSolver:
    """Feasibility MIP with binary cell variables, if Gurobi is usable."""

    def __init__(self, n: int, *, time_limit_sec: float | None = None) -> None:
        if n < 1:
            raise ValueError("N must be at least 1")
        self.n = n
        self.time_limit_sec = time_limit_sec
        self._model: Any | None = None
        self._x: Any | None = None
        self._gp: Any | None = None
        self._build_time_sec = 0.0
        self._num_constraints: int | None = None

    def build(self) -> None:
        started = perf_counter()
        import gurobipy as gp
        from gurobipy import GRB

        model = gp.Model("nqueens")
        model.Params.OutputFlag = 0
        if self.time_limit_sec is not None:
            model.Params.TimeLimit = self.time_limit_sec
        x = model.addVars(self.n, self.n, vtype=GRB.BINARY, name="x")
        for row in range(self.n):
            model.addConstr(gp.quicksum(x[row, column] for column in range(self.n)) == 1, name=f"row_{row}")
        for column in range(self.n):
            model.addConstr(gp.quicksum(x[row, column] for row in range(self.n)) == 1, name=f"column_{column}")
        for delta in range(-(self.n - 1), self.n):
            cells = [(row, row - delta) for row in range(self.n) if 0 <= row - delta < self.n]
            if len(cells) > 1:
                model.addConstr(gp.quicksum(x[row, column] for row, column in cells) <= 1, name=f"main_{delta}")
        for total in range(1, 2 * self.n - 2):
            cells = [(row, total - row) for row in range(self.n) if 0 <= total - row < self.n]
            if len(cells) > 1:
                model.addConstr(gp.quicksum(x[row, column] for row, column in cells) <= 1, name=f"anti_{total}")
        model.setObjective(0.0, GRB.MINIMIZE)
        model.update()
        self._model, self._x, self._gp = model, x, gp
        self._num_constraints = model.NumConstrs
        self._build_time_sec = perf_counter() - started

    def solve(self) -> NQueensResult:
        total_started = perf_counter()
        try:
            if self._model is None:
                self.build()
        except ModuleNotFoundError as error:
            return NQueensResult(self.n, "gurobi", "gurobi", "SKIPPED", total_time_sec=perf_counter() - total_started,
                                 error_message=f"gurobipy is not installed: {error}")
        except Exception as error:
            status = "SKIPPED" if _likely_license_failure(error) else "ERROR"
            return NQueensResult(self.n, "gurobi", "gurobi", status, total_time_sec=perf_counter() - total_started,
                                 error_message=f"Gurobi unavailable: {error}")

        assert self._model is not None and self._x is not None and self._gp is not None
        started = perf_counter()
        try:
            self._model.optimize()
            solve_time = perf_counter() - started
            has_solution = self._model.SolCount > 0
            if has_solution:
                board = board_from_positions(
                    self.n,
                    [(row, column) for row in range(self.n) for column in range(self.n) if self._x[row, column].X > 0.5],
                )
                valid = validate_solution(board)
                status = "OPTIMAL" if self._model.Status == self._gp.GRB.OPTIMAL else "FEASIBLE"
                if not valid:
                    status = "ERROR"
                error = None if valid else "Gurobi returned a solution that failed independent validation"
            else:
                board, valid = None, None
                if self._model.Status == self._gp.GRB.INFEASIBLE:
                    status, error = "UNSAT", None
                elif self._model.Status == self._gp.GRB.TIME_LIMIT:
                    status, error = "TIMEOUT", None
                else:
                    status, error = "ERROR", f"Gurobi status code: {self._model.Status}"
            return NQueensResult(
                self.n, "gurobi", "gurobi", status,
                build_time_sec=self._build_time_sec, solve_time_sec=solve_time,
                total_time_sec=self._build_time_sec + solve_time, num_variables=self.n * self.n,
                num_constraints=self._num_constraints, solution=board, solution_valid=valid, error_message=error,
            )
        except Exception as error:
            solve_time = perf_counter() - started
            status = "SKIPPED" if _likely_license_failure(error) else "ERROR"
            return NQueensResult(self.n, "gurobi", "gurobi", status, build_time_sec=self._build_time_sec,
                                 solve_time_sec=solve_time, total_time_sec=self._build_time_sec + solve_time,
                                 num_variables=self.n * self.n, num_constraints=self._num_constraints,
                                 error_message=str(error))

    def close(self) -> None:
        if self._model is not None:
            self._model.dispose()
            self._model = None
