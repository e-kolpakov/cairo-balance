import json

import tempfile

import argparse

from eth_typing import HexStr
from starkware.cairo.bootloaders.generate_fact import get_program_output
from typing import List

import os, sys
from web3 import Web3, HTTPProvider

import config

sys.path.insert(0, os.getcwd())

from merkle_tree import EthereumBuilder
from utils import IntUtils

from starkware.cairo.sharp.sharp_client import init_client


TREE_CHECK_CAIRO_SOURCE_PATH = os.path.join(os.path.dirname(__file__), "tree_check.cairo")

parser = argparse.ArgumentParser(description="AMM demo")
parser.add_argument(
    "--bin_dir",
    type=str,
    default="",
    help="The path to a directory that contains the cairo-compile and cairo-run scripts. "
         "If not specified, files are assumed to be in the system's PATH.",
)
parser.add_argument(
    "--node_rpc_url",
    type=str,
    default=config.WEB3_GOERLI_API,
    help="RPC URL to communicate with an Ethereum node on Goerli"
)
parser.add_argument(
    "--debug",
    default=False,
    action='store_true',
    help="RPC URL to communicate with an Ethereum node on Goerli"
)

def read_cairo_hash(cairo_output: List[int]) -> HexStr:
    input_length = len(cairo_output)
    assert input_length == 2, "output length should be exactly 2"
    high, low = cairo_output[0], cairo_output[1]
    as_bytes = high.to_bytes(16, 'big', signed=False) + low.to_bytes(16, 'big', signed=False)
    return IntUtils.to_hex_str(int.from_bytes(as_bytes, 'big', signed=False))


def example_inputs():
    from eth_progressive_merkle_tree_reference_impl import testdata
    return [
        # [],
        testdata[:1],
        # testdata[:2],
        # testdata[:3],
        # testdata[:5],
        # testdata[:256],
        # testdata[:5049]
    ]


def write_cairo_input(test_data, target_file):
    program_input = {
        "data": [
            IntUtils.from_bytes(record, 'big', signed=False)
            for record in test_data
        ]
    }
    json.dump(program_input, target_file, indent=4, sort_keys=True)


def get_eth_tree(test_data):
    tree_builder = EthereumBuilder()
    tree_builder.add_values(test_data)
    return tree_builder.build().hash()


def main():
    # w3 = Web3(HTTPProvider(args.node_rpc_url))
    # if not w3.isConnected():
    #     print("Error: could not connect to the Ethereum node.")
    #     exit(1)
    args = parser.parse_args()

    cairo_sharp_client = init_client(bin_dir=args.bin_dir, node_rpc_url=args.node_rpc_url)
    compile_flags = [
        f'--cairo_path={config.PROJECT_ROOT}'
    ]
    program = cairo_sharp_client.compile_cairo(source_code_path=TREE_CHECK_CAIRO_SOURCE_PATH, flags=compile_flags)

    has_error = False

    for (idx, example) in enumerate(example_inputs()):
        with tempfile.NamedTemporaryFile(mode="w") as program_input_file:
            write_cairo_input(example, program_input_file)
            program_input_file.flush()
            if args.debug:
                with open(program_input_file.name, 'r') as input_file:
                    print(input_file.readlines())
            cairo_pie = cairo_sharp_client.run_program(program, program_input_file.name)
            output = get_program_output(cairo_pie)
        cairo_mtr = read_cairo_hash(output)
        eth_mtr = IntUtils.hex_str_from_bytes(get_eth_tree(example), 'big', signed=False)
        if cairo_mtr != eth_mtr:
            has_error = True
            print(f"Cairo MTR was not equal to Eth MTR for input example {idx}\nCairo:{cairo_mtr}\nEth  :{eth_mtr}")

    if has_error:
        print("Error - one or more Merkle Tree root were different. See above for details")
        sys.exit(1)
    else:
        print("All inputs run successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
