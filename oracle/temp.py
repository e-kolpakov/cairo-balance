from eth_hash.auto import keccak
from keccak_utils import to_ints
from model import ProverOutput

values = [
    239505350084042537683742866394048006571,
    99423443792670918950949466338103002933,
    240360626826466254229991599557678691471,
    241363757820317199307467294649858493936,
    3000
]

# keccak_input = bytearray()
# for val in values:
#     keccak_input += val.to_bytes(16, 'big')
#
# print(to_ints(keccak_input, 16, "\n"))
#
# computed = keccak(keccak_input)
#
# print(to_ints(computed, 16, "\n"))
#
# max_val = 2 ** 128
# max_eth_summply_in_gwei = 10**12 * 10**18
# print(max_val > max_eth_summply_in_gwei)

output = ProverOutput.read_from_prover_output(values)
print("Beacon State MTR", output.beacon_state_mtr)
print("Validators MTR", output.validator_keys_mtr)