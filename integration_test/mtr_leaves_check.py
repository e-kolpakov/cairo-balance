from decimal import Decimal

import logging
from eth_typing import HexStr
from typing import List, Dict, Any

import os, sys
import config
from api.eth_api import BeaconState, Validator
from integration_test.testutils import CairoTestHelper, ExampleRunnerHelper, get_arg_parser

sys.path.insert(0, os.getcwd())

from merkle.merkle_tree import ProgressiveMerkleTreeBuilder
from utils import IntUtils

PROGRAM_PATH = os.path.join(os.path.dirname(__file__), "mtr_leaves_check.cairo")

class CairoHelper(CairoTestHelper[HexStr]):
    SEPARATOR = 2128685017815709937522 # cairo representation of 'separator' string

    def _parse_output(self, output: List[int]) -> List[bytes]:
        result = []
        current_result = bytes()
        for line in output:
            if line == self.SEPARATOR:
                result.append(current_result)
                current_result = bytes()
            else:
                current_result += line.to_bytes(16, 'big', signed=False)
        return result


class ExampleRunner(ExampleRunnerHelper[BeaconState, HexStr]):
    def examples(self):
        key1, key2, key3 = 1, 10, 101
        return [
            (f"validators_0", BeaconState([])),
            (f"validators_1", BeaconState([
                Validator(HexStr(f"{key1:#096x}"), Decimal(10000000)),
            ])),
            (f"validators_2", BeaconState(
                [
                    Validator(HexStr(f"{key1:#096x}"), Decimal(1000)),
                    Validator(HexStr(f"{key2:#096x}"), Decimal(2000)),
                ]
            )),
            (f"validators_3", BeaconState(
                [
                    Validator(HexStr(f"{key1:#096x}"), Decimal(1000)),
                    Validator(HexStr(f"{key2:#096x}"), Decimal(2000)),
                    Validator(HexStr(f"{key3:#096x}"), Decimal(20000)),
                ]
            )),
            (f"real_hashes_4", BeaconState(
                [
                    Validator(HexStr("0x953805708367b0b5f6710d41608ccdd0d5a67938e10e68dd010890d4bfefdcde874370423b0af0d0a053b7b98ae2d6ed"), Decimal(1000)),
                    Validator(HexStr("0x814dc0f55ac3fb02431668adf6f8fa1c37fb9baa5b87f5be519a373205933dfe742f3df566cba3a35b5be1940e1dffd5"), Decimal(2000)),
                    Validator(HexStr("0x88d1ac7f33780fd328bee60957b2325cfa41b3719614b662616d4525e5b478b3a81d490671526936e3ea412428c84451"), Decimal(3000)),
                    Validator(HexStr("0xa53dd1acc6091fbff3efd43ff520c82ca4b56fe2ba9ee8ca119fd6a4646b6759b15f2cafeb1bbf14f5a0cb2c66cdfe47"), Decimal(3000)),
                ]
            )),

        ]

    def example_to_input(self, example: BeaconState) -> Dict[str, Any]:
        return {"beacon_state": example.to_cairo()}

    def example_to_expected_outpiut(self, example: BeaconState) -> List[bytes]:
        return example.merkle_tree_builder().get_leaves()

    def format_output(self, output: HexStr) -> str:
        return output


def main():
    parser = get_arg_parser()
    args = parser.parse_args()
    cairo_helper = CairoHelper(
        args.bin_dir, args.node_rpc_url, PROGRAM_PATH, cairo_path=config.PROJECT_ROOT
    )
    runner = ExampleRunner(cairo_helper, args.store_input_copy)

    runner.run()


if __name__ == "__main__":
    main()
