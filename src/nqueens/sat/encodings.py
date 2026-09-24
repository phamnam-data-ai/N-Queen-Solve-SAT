"""CNF encodings for at-most-one (AMO) and exactly-one constraints.

The pairwise, sequential, and binary encodings are wrappers around PySAT's
``CardEnc``.  Commander and product are intentionally implemented here so the
benchmark compares the named encodings rather than silently substituting one.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import ceil, sqrt

from pysat.card import CardEnc, EncType
from pysat.formula import IDPool

Clause = list[int]

ENCODING_DETAILS: dict[str, dict[str, str]] = {
    "pairwise": {
        "provider": "PySAT CardEnc (EncType.pairwise)",
        "auxiliary_strategy": "No auxiliary variables.",
    },
    "sequential": {
        "provider": "PySAT CardEnc (EncType.seqcounter)",
        "auxiliary_strategy": "Sequential-counter variables allocated by IDPool.",
    },
    "binary": {
        "provider": "PySAT CardEnc (EncType.bitwise)",
        "auxiliary_strategy": "Bit-position variables allocated by IDPool.",
    },
    "commander": {
        "provider": "Custom implementation in nqueens.sat.encodings",
        "auxiliary_strategy": "One commander per non-singleton group, recursively constrained.",
    },
    "product": {
        "provider": "Custom implementation in nqueens.sat.encodings",
        "auxiliary_strategy": "Row/column selector variables for a near-square literal grid.",
    },
}

_PYSAT_ENCODINGS = {
    "pairwise": EncType.pairwise,
    "sequential": EncType.seqcounter,
    "binary": EncType.bitwise,
}


def _normalise_encoding(encoding_type: str) -> str:
    aliases = {
        "seqcounter": "sequential",
        "bitwise": "binary",
    }
    normalised = aliases.get(encoding_type.lower(), encoding_type.lower())
    if normalised not in ENCODING_DETAILS:
        available = ", ".join(ENCODING_DETAILS)
        raise ValueError(f"unknown AMO encoding '{encoding_type}'; choose one of: {available}")
    return normalised


def _call_tag(vpool: IDPool, tag: str) -> str:
    """Produce a tag unique to this pool without relying on raw variable IDs."""
    counter = getattr(vpool, "_nqueens_encoding_calls", 0)
    setattr(vpool, "_nqueens_encoding_calls", counter + 1)
    return f"{tag}:{counter}"


def _pairwise_amo(literals: Sequence[int]) -> list[Clause]:
    return [[-left, -right] for index, left in enumerate(literals) for right in literals[index + 1 :]]


def _commander_amo(literals: Sequence[int], vpool: IDPool, tag: str, group_size: int) -> list[Clause]:
    """Hierarchical commander AMO with pairwise constraints inside groups."""
    if group_size < 2:
        raise ValueError("commander group_size must be at least 2")

    def recurse(items: list[int], level: int) -> list[Clause]:
        if len(items) <= group_size:
            return _pairwise_amo(items)

        clauses: list[Clause] = []
        representatives: list[int] = []
        for group_index, offset in enumerate(range(0, len(items), group_size)):
            group = items[offset : offset + group_size]
            clauses.extend(_pairwise_amo(group))
            if len(group) == 1:
                representatives.append(group[0])
                continue
            commander = vpool.id(("nqueens", tag, "commander", level, group_index))
            # A selected literal activates its group commander.  AMO among
            # representatives then prohibits selections across groups.
            clauses.extend([[-literal, commander] for literal in group])
            representatives.append(commander)
        clauses.extend(recurse(representatives, level + 1))
        return clauses

    return recurse(list(literals), 0)


def _product_amo(literals: Sequence[int], vpool: IDPool, tag: str, dimension: int | None) -> list[Clause]:
    """Two-product AMO using row and column selector variables.

    Literals are placed in a ``rows x columns`` grid.  A literal implies its
    row and column selectors; pairwise AMO on both selector sets prevents two
    selected literals from sharing either equal or different grid coordinates.
    """
    count = len(literals)
    if count <= 1:
        return []
    rows = dimension if dimension is not None else ceil(sqrt(count))
    if rows < 1:
        raise ValueError("product dimension must be positive")
    rows = min(rows, count)
    columns = ceil(count / rows)
    row_selectors = [vpool.id(("nqueens", tag, "product-row", index)) for index in range(rows)]
    column_selectors = [vpool.id(("nqueens", tag, "product-column", index)) for index in range(columns)]

    clauses: list[Clause] = []
    for index, literal in enumerate(literals):
        row, column = divmod(index, columns)
        clauses.append([-literal, row_selectors[row]])
        clauses.append([-literal, column_selectors[column]])
    clauses.extend(_pairwise_amo(row_selectors))
    clauses.extend(_pairwise_amo(column_selectors))
    return clauses


def encode_amo(
    literals: Sequence[int],
    encoding_type: str,
    vpool: IDPool,
    *,
    commander_group_size: int = 3,
    product_dimension: int | None = None,
    tag: str = "amo",
) -> list[Clause]:
    """Encode ``sum(literals) <= 1`` as CNF clauses.

    ``vpool`` must start after all original variables.  This function never
    falls back to another named encoding: unsupported names fail explicitly.
    """
    encoding = _normalise_encoding(encoding_type)
    values = list(literals)
    if len(values) <= 1:
        return []
    unique_tag = _call_tag(vpool, tag)
    if encoding in _PYSAT_ENCODINGS:
        return CardEnc.atmost(
            lits=values,
            bound=1,
            vpool=vpool,
            encoding=_PYSAT_ENCODINGS[encoding],
        ).clauses
    if encoding == "commander":
        return _commander_amo(values, vpool, unique_tag, commander_group_size)
    return _product_amo(values, vpool, unique_tag, product_dimension)


def encode_exactly_one(
    literals: Sequence[int],
    encoding_type: str,
    vpool: IDPool,
    **options: object,
) -> list[Clause]:
    """Encode exactly one literal as one ALO clause plus the chosen AMO CNF."""
    if not literals:
        return [[]]
    return [list(literals), *encode_amo(literals, encoding_type, vpool, **options)]
