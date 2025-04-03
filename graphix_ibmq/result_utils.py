from typing import Dict

from graphix.pattern import Pattern


def format_result(
    result: Dict[str, int], pattern: Pattern, register_dict: Dict[int, int]
) -> Dict[str, int]:
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
    N_node = pattern.n_node
    output_keys = [register_dict[node] for node in pattern.output_nodes]

    formatted: Dict[str, int] = {}
    for bitstring, count in result.items():
        masked = "".join(bitstring[N_node - 1 - idx] for idx in output_keys)
        formatted[masked] = formatted.get(masked, 0) + count

    return formatted
