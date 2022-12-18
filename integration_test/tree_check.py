import logging
from typing import List, Dict, Any

import os, sys
import config
from integration_test.testutils import CairoTestHelper, ExampleRunnerHelper, get_arg_parser

sys.path.insert(0, os.getcwd())

from merkle.merkle_tree import ProgressiveMerkleTreeBuilder
from utils import IntUtils

TREE_CHECK_CAIRO_SOURCE_PATH = os.path.join(os.path.dirname(__file__), "tree_check.cairo")

class CairoHelper(CairoTestHelper[int]):
    def _parse_output(self, output: List[int]) -> int:
        input_length = len(output)
        assert input_length == 2, "output length should be exactly 2"
        high, low = output[0], output[1]
        as_bytes = high.to_bytes(16, 'big', signed=False) + low.to_bytes(16, 'big', signed=False)
        return IntUtils.from_bytes(as_bytes, 'big', signed=False)


class ExampleRunner(ExampleRunnerHelper[List[bytes], int]):
    def examples(self):
        from merkle.eth_progressive_merkle_tree_reference_impl import testdata
        return [
            (f"count_0", []),
            (f"count_1", testdata[:1]),
            (f"count_2", testdata[:2]),
            (f"count_3", testdata[:3]),
            (f"count_5", testdata[:5]),
            (f"count_256", testdata[:256]),
            # (f"count_5049", testdata[:5049]),
        ]

    def example_to_input(self, example: List[bytes]) -> Dict[str, Any]:
        return {
            "data": [
                IntUtils.from_bytes(record, 'big', signed=False)
                for record in example
            ]
        }

    def example_to_expected_outpiut(self, example) -> int:
        tree_builder = ProgressiveMerkleTreeBuilder()
        tree_builder.add_values(example)
        return tree_builder.build().hash_int()


def main():
    parser = get_arg_parser()
    args = parser.parse_args()
    cairo_helper = CairoHelper(
        args.bin_dir, args.node_rpc_url, TREE_CHECK_CAIRO_SOURCE_PATH, cairo_path=config.PROJECT_ROOT
    )
    runner = ExampleRunner(cairo_helper, args.store_input_copy)

    runner.run()


if __name__ == "__main__":
    main()
