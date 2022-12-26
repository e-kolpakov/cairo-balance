from utils import IntUtils

high, low = 203012346610664165468348008372416444642, 138806984785747192686823481349753689003

print("0x98bac1784b14c1920de56ef8c0ae78e2686d40bab49127e0ee9d92686c3253ab")
print(IntUtils.read_pair_into_hex_str(high, low))

def print_bytes(value):
    print(value.to_bytes(32, 'big'))

# print_bytes(high)
# print_bytes(high << 8 * 16)

shifted_high = high << (8*16)

print(IntUtils.to_hex_str(shifted_high + low))
