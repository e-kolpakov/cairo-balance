import sys

from typing import List

from keccak_utils import KeccakHash
from merkle_tree import EthereumBuilder
from utils import IntUtils


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

if __name__ == "__main__":
    with open("./cairo_zerohashes.txt", 'r') as input_file:
        cairo_zerohashes_bytes = read_zerohashes(read_cairo_program_output(input_file))
        cairo_zerohashes = [
            IntUtils.to_hex_str(int.from_bytes(cairo_bytes, 'big', signed=False))
            for cairo_bytes in cairo_zerohashes_bytes
        ]


    eth_tree_builder = EthereumBuilder()
    eth_zerohashes = [tree_node.hash_hex() for tree_node in eth_tree_builder.zerohashes]

    # for (idx, (cairo_hash, eth_hash)) in enumerate(zip(cairo_zerohashes, eth_zerohashes)):
    #     print(f"Cairo {idx:02}={cairo_hash}")
    #     print(f"Eth   {idx:02}={eth_hash}")

    if verify_zerohashes_match(cairo_zerohashes, eth_zerohashes):
        print("Zerohashes match")

