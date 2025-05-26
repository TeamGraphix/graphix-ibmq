from graphix_ibmq.result_utils import format_result


class DummyPattern:
    def __init__(self, n_node, output_nodes):
        self.n_node = n_node
        self.output_nodes = output_nodes


def test_format_result_basic():
    raw = {"01": 10, "10": 5}
    patt = DummyPattern(n_node=2, output_nodes=[0, 1])
    register_dict = {0: 0, 1: 1}
    formatted = format_result(raw, patt, register_dict)
    assert formatted == {"10": 10, "01": 5}
