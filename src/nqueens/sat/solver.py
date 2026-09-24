"""N-Queens solver using a transparent CNF model and PySAT backends."""

from __future__ import annotations

from collections import defaultdict
from time import perf_counter

from pysat.formula import IDPool
from pysat.solvers import Solver

from ..problem import NQueensResult, board_from_positions, var_id
from ..validators import validate_solution
from .encodings import ENCODING_DETAILS, encode_amo, encode_exactly_one


class SATNQueensSolver:
    """Build and solve an N-Queens CNF instance using a selected AMO encoding."""

    def __init__(
        self,
        n: int,
        encoding: str = "sequential",
        sat_solver: str = "glucose3",
        *,
        commander_group_size: int = 3,
        product_dimension: int | None = None,
    ) -> None:
        if n < 1:
            raise ValueError("N must be at least 1")
        if encoding.lower() not in ENCODING_DETAILS and encoding.lower() not in {"seqcounter", "bitwise"}:
            raise ValueError(f"unknown SAT encoding '{encoding}'")
        if commander_group_size < 2:
            raise ValueError("commander_group_size must be at least 2")
        if product_dimension is not None and product_dimension < 1:
            raise ValueError("product_dimension must be positive")
        self.n = n
        self.encoding = {"seqcounter": "sequential", "bitwise": "binary"}.get(encoding.lower(), encoding.lower())
        self.sat_solver = sat_solver
        self.commander_group_size = commander_group_size
        self.product_dimension = product_dimension
        self._clauses: list[list[int]] = []
        self._vpool: IDPool | None = None
        self._solver: Solver | None = None
        self._clause_breakdown: dict[str, int] = {}
        self._build_time_sec = 0.0
        self._built = False

    def _add(self, clauses: list[list[int]], category: str) -> None:
        self._clauses.extend(clauses)
        self._clause_breakdown[category] += len(clauses)

    def _encoding_options(self, tag: str) -> dict[str, object]:
        return {
            "commander_group_size": self.commander_group_size,
            "product_dimension": self.product_dimension,
            "tag": tag,
        }

    def _diagonal_literals(self, main: bool) -> list[list[int]]:
        diagonals: defaultdict[int, list[int]] = defaultdict(list)
        for row in range(self.n):
            for column in range(self.n):
                key = row - column if main else row + column
                diagonals[key].append(var_id(self.n, row, column))
        return [literals for literals in diagonals.values() if len(literals) > 1]

    def build(self) -> None:
        """Construct CNF, allocate auxiliaries safely, and initialise PySAT."""
        if self._solver is not None:
            self._solver.delete()
        started = perf_counter()
        self._clauses = []
        self._clause_breakdown = defaultdict(int)
        # Board variables occupy 1..N^2.  Every cardinality auxiliary is then
        # allocated by this pool, preventing original/auxiliary ID collisions.
        self._vpool = IDPool(start_from=self.n * self.n + 1)

        for row in range(self.n):
            literals = [var_id(self.n, row, column) for column in range(self.n)]
            clauses = encode_exactly_one(literals, self.encoding, self._vpool, **self._encoding_options(f"row-{row}"))
            self._add(clauses, "row")
        for column in range(self.n):
            literals = [var_id(self.n, row, column) for row in range(self.n)]
            clauses = encode_exactly_one(literals, self.encoding, self._vpool, **self._encoding_options(f"column-{column}"))
            self._add(clauses, "column")
        for family, is_main in (("main_diagonal", True), ("anti_diagonal", False)):
            for index, literals in enumerate(self._diagonal_literals(is_main)):
                clauses = encode_amo(literals, self.encoding, self._vpool, **self._encoding_options(f"{family}-{index}"))
                self._add(clauses, family)

        # Loading the CNF into the backend is part of model construction, not
        # SAT search, so it belongs to build_time.
        self._solver = Solver(name=self.sat_solver, bootstrap_with=self._clauses)
        self._build_time_sec = perf_counter() - started
        self._built = True

    def _statistics(self) -> dict[str, object]:
        top = self._vpool.top if self._vpool is not None else self.n * self.n
        return {
            "original_board_variables": self.n * self.n,
            "auxiliary_variables": top - self.n * self.n,
            "total_sat_variables": top,
            "total_sat_clauses": len(self._clauses),
            "clause_breakdown": dict(self._clause_breakdown),
            "encoding_provider": ENCODING_DETAILS[self.encoding]["provider"],
            "auxiliary_strategy": ENCODING_DETAILS[self.encoding]["auxiliary_strategy"],
        }

    def solve(self) -> NQueensResult:
        """Solve the built model and independently validate any SAT model."""
        total_started = perf_counter()
        try:
            if not self._built:
                self.build()
        except Exception as error:  # PySAT reports unavailable backends at construction time.
            return NQueensResult(
                n=self.n,
                method="sat",
                encoding=self.encoding,
                backend=self.sat_solver,
                status="SKIPPED",
                total_time_sec=perf_counter() - total_started,
                error_message=f"PySAT backend unavailable or could not initialise: {error}",
            )

        assert self._solver is not None
        solve_started = perf_counter()
        try:
            satisfiable = self._solver.solve()
            solve_time = perf_counter() - solve_started
            solution = None
            valid = None
            if satisfiable:
                model = set(self._solver.get_model() or [])
                positions = [
                    (row, column)
                    for row in range(self.n)
                    for column in range(self.n)
                    if var_id(self.n, row, column) in model
                ]
                solution = board_from_positions(self.n, positions)
                valid = validate_solution(solution)
                status = "SAT" if valid else "ERROR"
                error_message = None if valid else "SAT backend returned a model that failed independent validation"
            else:
                status = "UNSAT"
                error_message = None
            stats = self._statistics()
            return NQueensResult(
                n=self.n,
                method="sat",
                encoding=self.encoding,
                backend=self.sat_solver,
                status=status,
                build_time_sec=self._build_time_sec,
                solve_time_sec=solve_time,
                total_time_sec=self._build_time_sec + solve_time,
                num_variables=int(stats["total_sat_variables"]),
                num_clauses=int(stats["total_sat_clauses"]),
                solution=solution,
                solution_valid=valid,
                error_message=error_message,
                statistics=stats,
            )
        except Exception as error:
            solve_time = perf_counter() - solve_started
            return NQueensResult(
                n=self.n,
                method="sat",
                encoding=self.encoding,
                backend=self.sat_solver,
                status="ERROR",
                build_time_sec=self._build_time_sec,
                solve_time_sec=solve_time,
                total_time_sec=self._build_time_sec + solve_time,
                num_variables=self._vpool.top if self._vpool else None,
                num_clauses=len(self._clauses),
                error_message=str(error),
                statistics=self._statistics(),
            )

    def close(self) -> None:
        """Release native SAT backend resources when the caller is finished."""
        if self._solver is not None:
            self._solver.delete()
            self._solver = None
