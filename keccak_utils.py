from typing import List, Iterable, Union

from eth_hash.auto import keccak

KeccakHash = bytes
KeccakInput = Union[bytes, bytearray]

def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def to_ints(bytes_list, n_bytes_per_group = 16, separator=' '):
    chunks = chunk_list(bytes_list, n_bytes_per_group)
    ints = [int.from_bytes(chunk, 'big', signed=False) for chunk in chunks]
    strs = [str(hex_int) for hex_int in ints]
    return separator.join(strs)


def to_bytes(value, size=32):
    return value.to_bytes(size, 'big')


def keccak_values(*values: Iterable[bytes]):
    keccak_input = bytearray()
    for val in values:
        assert isinstance(val, bytes), f"expected bytes, got {val}"
        keccak_input += val
    # print("Computing keccak on:")
    # print(to_ints(keccak_input, 16, "\n"))
    result = keccak(keccak_input)
    # print(f"Result")
    # print(to_ints(result, 16, "\n"))
    return result

def keccak2(left: bytes, right: bytes) -> bytes:
    """
    Similar to keccak2 in keccak.cairo, takes two keccak hashes and calculates keccak hash over them
    """
    return keccak_values(left, right)


# def account_keccak(account: Account) -> bytes:
#     """
#     Similar to account_keccak in keccak.cairo, takes an Account and calculates keccak hash over it
#     """
#     size = 32 # use with non-optimized account_keccak
#     # size = 16
#     return keccak_values(to_bytes(account.address, size), to_bytes(account.balance, size))