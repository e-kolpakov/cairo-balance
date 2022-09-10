from typing import List

import os, sys
sys.path.insert(0, os.getcwd())

from keccak_utils import KeccakHash
from merkle_tree import EthereumBuilder
from utils import IntUtils

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


TREE_CHECK_CAIRO_SOURCE_PATH = os.path.join(os.path.dirname(__file__), "zerohashes_check.cairo")

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


def read_cairo_program_output(input_file) -> List[int]:
    result = []
    for (lineno, line) in enumerate(input_file):
        if lineno == 0:
            continue # skip "Program output
        try:
            result.append(int(line.lstrip()))
        except ValueError:
            continue
    return result


def read_zerohashes(cairo_output: List[int]) -> List[KeccakHash]:
    input_length = len(cairo_output)
    assert input_length % 2 == 0, "input length should be even"
    result = []
    for idx in range(input_length // 2):
        # output is big-endian
        high, low = cairo_output[2*idx], cairo_output[2*idx+1]
        as_bytes = high.to_bytes(16, 'big', signed=False) + low.to_bytes(16, 'big', signed=False)
        result.append(as_bytes)

    return result

def verify_zerohashes_match(cairo_zerohashes, eth_zerohashes):
    assert len(cairo_zerohashes) == len(eth_zerohashes)
    for (idx, (cairo_hex, eth_hex)) in enumerate(zip(cairo_zerohashes, eth_zerohashes)):
        if cairo_hex != eth_hex:
            print(f"Not equal at index {idx}:\ncairo={cairo_hex}\neth  ={eth_hex}")
            return False

    return True


def get_eth_tree():
    tree_builder = EthereumBuilder()
    return [
        node.hash_hex() for node in tree_builder.zerohashes
    ]


def main():
    args = parser.parse_args()

    cairo_sharp_client = init_client(bin_dir=args.bin_dir, node_rpc_url=args.node_rpc_url)
    compile_flags = [
        f'--cairo_path={config.PROJECT_ROOT}'
    ]
    print(f"Compiling cairo program {TREE_CHECK_CAIRO_SOURCE_PATH}")
    program = cairo_sharp_client.compile_cairo(source_code_path=TREE_CHECK_CAIRO_SOURCE_PATH, flags=compile_flags)

    with tempfile.NamedTemporaryFile(mode="w") as program_input_file:
        test_data = []
        json.dump(test_data, program_input_file, indent=4, sort_keys=True)
        program_input_file.flush()
        print(f"Running cairo program with input {test_data}")
        cairo_pie = cairo_sharp_client.run_program(program, program_input_file.name)
        output = get_program_output(cairo_pie)
        print("Parsing cairo output")
        cairo_zerohashes = [
            IntUtils.to_hex_str(int.from_bytes(cairo_bytes, 'big', signed=False))
            for cairo_bytes in (read_zerohashes(output))
        ]

    print("Obtaining zerohashes from Eth")
    eth_zerohashes = get_eth_tree()

    # for (idx, (cairo_hash, eth_hash)) in enumerate(zip(cairo_zerohashes, eth_zerohashes)):
    #     print(f"Cairo {idx:02}={cairo_hash}")
    #     print(f"Eth   {idx:02}={eth_hash}")

    print("Verifying zerohashes match between cairo and eth")
    if verify_zerohashes_match(cairo_zerohashes, eth_zerohashes):
        print("Success - zerohashes match")
        sys.exit(0)
    else:
        print("Error - zerohashes are different. See above for details")
        sys.exit(1)


if __name__ == "__main__":
    main()

