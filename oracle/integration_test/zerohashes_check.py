import os, sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from eth_typing import HexStr

import config
from utils import IntUtils
from keccak_utils import KeccakHash
from merkle.merkle_tree import ProgressiveMerkleTreeBuilder

from integration_test.testutils import CairoTestHelper, ExampleRunnerHelper, get_arg_parser

class CairoHelper(CairoTestHelper[List[HexStr]]):
    def _parse_output(self, output: List[int]) -> List[HexStr]:
        return [
            IntUtils.to_hex_str(int.from_bytes(cairo_bytes, 'big', signed=False))
            for cairo_bytes in (self._read_zerohashes(output))
        ]
    @staticmethod
    def _read_zerohashes(cairo_output: List[int]) -> List[KeccakHash]:
        input_length = len(cairo_output)
        assert input_length % 2 == 0, "input length should be even"
        result = []
        for idx in range(input_length // 2):
            # output is big-endian
            high, low = cairo_output[2 * idx], cairo_output[2 * idx + 1]
            as_bytes = high.to_bytes(16, 'big', signed=False) + low.to_bytes(16, 'big', signed=False)
            result.append(as_bytes)

        return result

ExampleType = List[HexStr]
class ExampleRunner(ExampleRunnerHelper[int, ExampleType]):
    def examples(self):
        return [
            (f"example", 1),
        ]

    def example_to_input(self, example: int) -> Dict[str, Any]:
        return {}

    def example_to_expected_outpiut(self, example) -> ExampleType:
        tree_builder = ProgressiveMerkleTreeBuilder()
        return [
            node.hash_hex() for node in tree_builder.zerohashes
        ]

    def format_output(self, output: ExampleType) -> str:
        return f"{output}"

    def assert_equal(self, cairo: ExampleType, expected: ExampleType) -> bool:
        assert len(cairo) == len(expected)
        for (idx, (cairo_hex, eth_hex)) in enumerate(zip(cairo, expected)):
            if cairo_hex != eth_hex:
                print(f"Not equal at index {idx}:\ncairo={cairo_hex}\neth  ={eth_hex}")
                return False

        return True


def main():
    parser = get_arg_parser()
    args = parser.parse_args()
    cairo_helper = CairoHelper(
        args.bin_dir, args.node_rpc_url, config.CairoApps.IntegrationTests.ZEROHASHES
    )
    runner = ExampleRunner(cairo_helper, args.store_input_copy)

    runner.run()



if __name__ == "__main__":
    main()

