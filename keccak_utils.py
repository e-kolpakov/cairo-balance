from typing import List, Iterable

from eth_hash.auto import keccak

from account import Account


def _chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def to_ints(bytes_list, n_bytes_per_group = 16, separator=' '):
    chunks = _chunk_list(bytes_list, n_bytes_per_group)
    ints = [int.from_bytes(chunk, 'big', signed=False) for chunk in chunks]
    strs = [str(hex_int) for hex_int in ints]
    return separator.join(strs)

def _keccak_values(*values: Iterable[bytes]):
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
    return _keccak_values(left, right)


def account_keccak(account: Account) -> bytes:
    """
    Similar to account_keccak in keccak.cairo, takes an Account and calculates keccak hash over it

    Replicating Cairo's keccak calculation:
    https://github.com/starkware-libs/cairo-lang/blob/master/src/starkware/cairo/common/keccak.cairo
    https://github.com/starkware-libs/cairo-lang/blob/master/src/starkware/cairo/common/keccak.cairo#L86

    Line 51: splits a felt into high and low words, each being 16-byte elements (i.e. entire felt is 32-byte)
    Line 52: puts high bytes first (i.e. big-endian)

    Conclusion: our values should be 32-byte big-endians as well.
    """
    return _keccak_values(
        account.address.to_bytes(32, 'big'),
        account.balance.to_bytes(32, 'big')
    )