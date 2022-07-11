from eth_hash.auto import keccak
from keccak_utils import to_ints

values = [
    160624099442958928356030312786067501435,
    134140770933667314975125710268939313228,
    327439390396049466889558356295522056752,
    138833678699013848905045936501046370217,
]

keccak_input = bytearray()
for val in values:
    keccak_input += val.to_bytes(16, 'big')

print(to_ints(keccak_input, 16, "\n"))

computed = keccak(keccak_input)

print(to_ints(computed, 16, "\n"))

max_val = 2 ** 128
max_eth_summply_in_gwei = 10**12 * 10**18
print(max_val > max_eth_summply_in_gwei)