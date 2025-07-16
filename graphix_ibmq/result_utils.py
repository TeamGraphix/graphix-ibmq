from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graphix.pattern import Pattern


def format_result(result: dict[str, int], pattern: Pattern, register_dict: dict[int, int]) -> dict[str, int]:
    """Format raw measurement results into output-only bitstrings.

    Parameters
    ----------
    result : dict of str to int
        Raw result counts as returned by Qiskit (full bitstrings).
    pattern : Pattern
        Graphix pattern object containing output node information.
    register_dict : dict of int to int
        Mapping from pattern node index to classical register index.

    Returns
    -------
    formatted : dict of str to int
        Dictionary of bitstrings only for output nodes and their counts.
    """
    n_node = pattern.n_node
    output_keys = [register_dict[node] for node in pattern.output_nodes]

    formatted: dict[str, int] = {}
    for bitstring, count in result.items():
        masked = "".join(bitstring[n_node - 1 - idx] for idx in output_keys)
        formatted[masked] = formatted.get(masked, 0) + count

    return formatted
