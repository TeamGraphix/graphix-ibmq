from graphix_ibmq.result_utils import format_result

class DummyPattern:
    def __init__(self, n_node, output_nodes):
        self.n_node = n_node
        self.output_nodes = output_nodes

def test_format_result_basic():
    # raw bitstrings: "01" が 10 回, "10" が 5 回
    raw = {"01": 10, "10": 5}
    # N_node = 2, 出力ノード [0,1]
    patt = DummyPattern(n_node=2, output_nodes=[0, 1])
    # ノード→クラシカルレジスタのマッピング
    register_dict = {0: 0, 1: 1}
    formatted = format_result(raw, patt, register_dict)
    # 期待：ビット列の上位ノード順に取り出し → "10":10, "01":5
    assert formatted == {"10": 10, "01": 5}
