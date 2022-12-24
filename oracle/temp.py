# from eth_hash.auto import keccak
# from keccak_utils import to_ints
# from model import ProverOutput
#
# values = [
#     239505350084042537683742866394048006571,
#     99423443792670918950949466338103002933,
#     240360626826466254229991599557678691471,
#     241363757820317199307467294649858493936,
#     3000
# ]
#
# # keccak_input = bytearray()
# # for val in values:
# #     keccak_input += val.to_bytes(16, 'big')
# #
# # print(to_ints(keccak_input, 16, "\n"))
# #
# # computed = keccak(keccak_input)
# #
# # print(to_ints(computed, 16, "\n"))
# #
# # max_val = 2 ** 128
# # max_eth_summply_in_gwei = 10**12 * 10**18
# # print(max_val > max_eth_summply_in_gwei)
#
# output = ProverOutput.read_from_prover_output(values)
# print("Beacon State MTR", output.beacon_state_mtr)
# print("Validators MTR", output.validator_keys_mtr)
# from eth_utils import keccak
#
# contract_zero = "0xf5a5fd42d16a20302798ef6ed309979b43003d2320d9f0e8ea9831a92759fb4b"
# expected = '0xad3228b676f7d3cd4284a5443f17f1962b36e491b30a40b2405849e597ba5fb5'
# from oracle.utils import IntUtils
#
# as_bytes = IntUtils.from_hex_str(contract_zero).to_bytes(32, 'big')
#
# swapped_bytes = as_bytes[::-1]
#
# print("Original   ", contract_zero)
# print("Swapped    ", IntUtils.hex_str_from_bytes(swapped_bytes, 'big', False))
# print("Keccak(0,0)", IntUtils.hex_str_from_bytes(keccak(b"\x00" * 32 + b"\x00" * 32), 'big', False))
# print("Expected   ", expected)
from merkle.merkle_tree import ProgressiveMerkleTreeBuilder
from utils import IntUtils

keys = [1]

tree_builder = ProgressiveMerkleTreeBuilder()
for key in keys:
    tree_builder.add_values(IntUtils.pubkey_to_keccak_input(key))
print(tree_builder.build().hash_hex())
