def format_result(result: dict[str, int], pattern, register_dict: dict[int, int]) -> dict[str, int]:
    N_node = pattern.Nnode
    output_keys = [register_dict[node] for node in pattern.output_nodes]

    formatted = {}
    for bitstring, count in result.items():
        masked = "".join(bitstring[N_node - 1 - idx] for idx in output_keys)
        formatted[masked] = formatted.get(masked, 0) + count
    return formatted