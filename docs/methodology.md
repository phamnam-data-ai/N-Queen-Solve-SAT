# Methodology: N-Queens SAT Encoding and Exact-Solver Comparison

## N-Queens mathematical model

For an `N x N` board, binary variable `x[r,c]` is one precisely when a queen occupies row `r`, column `c`, where `0 <= r,c < N`. Each row and each column has exactly one queen: `sum_c x[r,c] = 1` and `sum_r x[r,c] = 1`. Every main diagonal (constant `r-c`) and anti-diagonal (constant `r+c`) has sum at most one.

## SAT formulation

The SAT variable for a board cell is `v(r,c) = r*N + c + 1`, so original variables occupy `1..N²`. A CNF formula is a conjunction of clauses. An at-least-one (ALO) constraint is one clause `(l1 OR ... OR lk)`; at-most-one (AMO) prevents two literals being true; exactly-one is ALO plus AMO. Rows and columns use exactly-one, while diagonals use AMO. An `IDPool` begins at `N²+1` to make every auxiliary ID collision-safe.

## Pairwise encoding

For each pair `li, lj`, add `(~li OR ~lj)`. AMO on `k` literals has `C(k,2) = k(k-1)/2` binary clauses and no auxiliary variables; a row also has one ALO clause. Rows and columns alone contribute `N²(N-1)` AMO clauses, or `O(N³)`. Summing the pairwise costs of both diagonal families is also `O(N³)`. It has direct propagation but can become memory-heavy.

## Sequential encoding

Sequential AMO introduces a chain of prefix/counter auxiliaries: a selected literal propagates through the chain and rejects later selections. It has linear `O(k)` clauses and auxiliaries for a `k`-literal AMO (with PySAT-specific constants), instead of quadratic pairwise growth. This project uses PySAT `CardEnc` with `EncType.seqcounter` and the shared `IDPool`.

## Binary encoding

The CLI name `binary` means the genuine PySAT `EncType.bitwise` AMO. Inputs receive binary codes; a selected literal implies the corresponding bit-position values. Two different selected literals would require an inconsistent bit. It has logarithmically many selector bits and approximately `O(k log k)` implication clauses; exact constants are implementation-specific. It is not silently substituted by sequential encoding.

## Commander encoding

The custom commander encoding partitions literals into small groups (default size 3). It applies pairwise AMO inside each group, then gives each non-singleton group a commander variable and adds `literal -> commander`. Representatives are recursively constrained. Cross-group choices conflict at a representative level, while same-group choices conflict locally. With fixed group size it has linear-order clauses/auxiliaries. `--commander-group-size` lets experiments expose the level-versus-local-pairwise trade-off.

## Product encoding

The custom two-product encoding lays `k` literals into a near-square `p x q` grid (`p = ceil(sqrt(k))` by default). Each literal implies its grid-row selector and grid-column selector. Pairwise AMO on both selector sets ensures two different cells cannot both be selected. It has about `p+q = O(sqrt(k))` auxiliaries and `2k + O(p²+q²) = O(k)` clauses for near-square dimensions. `--product-dimension` selects `p` explicitly.

## CP-SAT

OR-Tools uses integer `queen[r] in [0,N-1]`. `AllDifferent(queen)` enforces unique columns, while `AllDifferent(queen[r]+r)` and `AllDifferent(queen[r]-r)` enforce diagonal safety. It has `N` primary integer variables and three global constraints. Build time is Python model construction; solve time is `CpSolver.solve` only.

## MIP and CP Optimizer

Gurobi and CPLEX MIP use the explicit binary matrix with row/column equalities and diagonal `<=1` inequalities; objective zero makes it a feasibility model. IBM CP Optimizer uses the compact all-different formulation. These adapters are optional: no package, executable, or license produces `SKIPPED`.

## Comparison discussion and complexity

The benchmark records original/auxiliary SAT variables, clauses, build time, and solve time. Pairwise has no auxiliaries but `O(N³)` global clause growth. Sequential, commander (fixed group size), and near-square product have linear cost per cardinality constraint and `O(N²)` summed model growth. Binary is roughly `O(k log k)` per AMO. Model size does not prove speed: propagation strength, clause learning, backend versions, and hardware all influence measured runtime. Report the smallest measured model and fastest measured solve time separately; do not claim a universal winner without evidence.
