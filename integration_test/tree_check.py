import logging

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

from merkle_tree import EthereumBuilder, MerkleTreeNode
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
    "--store_input_copy",
    type=str,
    default=None,
    help="Write a copy of cairo program_input to this file. Default: do not write a copy"
)

LOGGER = logging.getLogger(__name__)


def read_cairo_hash(cairo_output: List[int]) -> int:
    input_length = len(cairo_output)
    assert input_length == 2, "output length should be exactly 2"
    high, low = cairo_output[0], cairo_output[1]
    as_bytes = high.to_bytes(16, 'big', signed=False) + low.to_bytes(16, 'big', signed=False)
    return IntUtils.from_bytes(as_bytes, 'big', signed=False)


def example_inputs():
    from eth_progressive_merkle_tree_reference_impl import testdata
    return [
        # (f"count_0", []),
        # (f"count_1", testdata[:1]),
        # (f"count_2", testdata[:2]),
        # (f"count_3", testdata[:3]),
        # (f"count_5", testdata[:5]),
        (f"count_256", testdata[:256]),
        # (f"count_5049", testdata[:5049]),
    ]


def make_cairo_input(test_data):
    return {
        "data": [
            IntUtils.from_bytes(record, 'big', signed=False)
            for record in test_data
        ]
    }


def get_eth_tree(test_data) -> MerkleTreeNode:
    tree_builder = EthereumBuilder()
    tree_builder.add_values(test_data)
    return tree_builder.build()


def main():
    # w3 = Web3(HTTPProvider(args.node_rpc_url))
    # if not w3.isConnected():
    #     print("Error: could not connect to the Ethereum node.")
    #     exit(1)
    args = parser.parse_args()

    LOGGER.info(f"Initializing Cairo client")
    cairo_sharp_client = init_client(bin_dir=args.bin_dir, node_rpc_url=args.node_rpc_url)
    compile_flags = [
        f'--cairo_path={config.PROJECT_ROOT}'
    ]
    LOGGER.info(f"Compiling Cairo program: {TREE_CHECK_CAIRO_SOURCE_PATH}")
    program = cairo_sharp_client.compile_cairo(source_code_path=TREE_CHECK_CAIRO_SOURCE_PATH, flags=compile_flags)

    has_error = False

    examples = example_inputs()
    total_examples = len(examples)
    LOGGER.info(f"Starting verification - total {total_examples} examples")
    for (idx, (label, example)) in enumerate(examples):
        LOGGER.info(f"Running example {idx+1}/{total_examples}: {label}")
        LOGGER.debug(f"Getting Eth merkle tree root {label}")
        eth_merkle_tree = get_eth_tree(example)
        eth_mtr = IntUtils.from_bytes(eth_merkle_tree.hash(), 'big', signed=False)
        LOGGER.debug(f"Eth merkle tree root is {eth_mtr:#x}")

        program_input = make_cairo_input(example)
        if args.store_input_copy is not None:
            filename, file_extension = os.path.splitext(args.store_input_copy)
            target_file_name = f"{filename}_{label}{file_extension}"
            LOGGER.debug(f"Storing a copy of input file in {target_file_name}")
            with open(target_file_name, 'w') as target_file:
                json.dump(program_input, target_file, indent=4, sort_keys=True)

        with tempfile.NamedTemporaryFile(mode="w") as program_input_file:
            json.dump(program_input, program_input_file, indent=4, sort_keys=True)
            program_input_file.flush()
            LOGGER.info(f"Running cairo program")
            cairo_pie = cairo_sharp_client.run_program(program, program_input_file.name)
            output = get_program_output(cairo_pie)
            LOGGER.debug(f"Cairo program run successfully - parsing output")
            cairo_mtr = read_cairo_hash(output)
            LOGGER.debug(f"Cairo program merkle tree root {cairo_mtr:#x}")
        LOGGER.debug(f"Obtained merkle tree roots:\nEth  ={eth_mtr:#x}\nCairo={cairo_mtr:#x}")
        if cairo_mtr != eth_mtr:
            has_error = True
            LOGGER.error(f"Cairo MTR was not equal to Eth MTR for input example {label}\nCairo:{cairo_mtr:#x}\nEth  :{eth_mtr:#x}")

    if has_error:
        LOGGER.error("Error - one or more Merkle Tree root were different. See above for details")
        sys.exit(1)
    else:
        print("All inputs run successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
