import enum
import json
import os
import random
import sys
import argparse
from typing import TypeVar, Set

from tap import Tap

from account import Account
from keccak_utils import account_keccak
from merkle_tree import TopDownBuilder

T = TypeVar('T')

class RangeMode(enum.Enum):
    SMALL = 'small'
    MEDIUM = 'medium'
    WIDE = 'wide'
    ETH = 'eth'
    UNRESTRICTED = 'unrestricted'


class EthereumConstants:
    TOTAL_SUPPLY = int(1e10) # actually, ~100 times less, but it's only a matter of time (500 years at current rate)
    ETH_TO_WEI = int(1e18)


class Range:
    def __init__(self, low: int, high: int):
        self._low = low
        self._high = high

    @property
    def low(self) -> int:
        return self._low

    @property
    def high(self) -> int:
        return self._high

    @property
    def size(self):
        return self.high - self.low

    def __repr__(self):
        return f"[{self._low}:{self._high}]"


class ValueRange(Range):
    @classmethod
    def get_range(cls, mode: RangeMode):
        if mode == RangeMode.SMALL:
            return cls(0, 1000)
        elif mode == RangeMode.MEDIUM:
            return cls(0, 100000)
        elif mode == RangeMode.WIDE:
            return cls(0, int(1e15))
        elif mode == RangeMode.ETH:
            return cls(0, EthereumConstants.TOTAL_SUPPLY * EthereumConstants.ETH_TO_WEI)
        elif mode == RangeMode.UNRESTRICTED:
            return cls(0, sys.maxsize)

class AddressRange(Range):
    def __repr__(self):
        return f"[{hex(self._low)}:{hex(self._high)}]"

    @classmethod
    def get_range(cls, mode: RangeMode):
        if mode == RangeMode.SMALL:
            return cls(0, 1000)
        elif mode == RangeMode.MEDIUM:
            return cls(0, 100000)
        elif mode == RangeMode.WIDE:
            return cls(0, int(1e15))
        elif mode == RangeMode.ETH:
            return cls(0, 2**40)  # actually 2**160, this is for testing purposes
        elif mode == RangeMode.UNRESTRICTED:
            return cls(0, sys.maxsize)



class EnumAction(argparse.Action):
    """
    Argparse action for handling Enums
    """
    def __init__(self, **kwargs):
        # Pop off the type value
        enum_type = kwargs.pop("type", None)

        # Ensure an Enum subclass is provided
        if enum_type is None:
            raise ValueError("type must be assigned an Enum when using EnumAction")
        if not issubclass(enum_type, enum.Enum):
            raise TypeError("type must be an Enum when using EnumAction")

        # Generate choices from the Enum
        kwargs.setdefault("choices", tuple(e.value for e in enum_type))

        super(EnumAction, self).__init__(**kwargs)

        self._enum = enum_type

    def __call__(self, parser, namespace, values, option_string=None):
        # Convert value back into an Enum
        value = self._enum(values)
        setattr(namespace, self.dest, value)


class ArgumentParser(Tap):
    count: int
    address_range: RangeMode
    value_range: RangeMode
    single: bool

    def configure(self):
        self.add_argument(
            "-c", "--count", required=False, default=20,
            help="Number of addresses to generate",
        )
        self.add_argument(
            "-a", "--address_range", action=EnumAction, type=RangeMode,
            default=RangeMode.SMALL
        )
        self.add_argument(
            "-v", "--value_range", action=EnumAction, type=RangeMode,
            default=RangeMode.SMALL
        )
        self.add_argument(
            "-s", "--single", action='store_true', default=False
        )


def generate_account(address_range: AddressRange, value_range: ValueRange, existing_addresses: Set[int]) -> Account:
    address = random.randint(address_range.low, address_range.high)
    # this is efficient if `count` << address_range.size, which is the main use case anyway
    while address in existing_addresses:
        address = random.randint(address_range.low, address_range.high)
    balance = random.randint(value_range.low, value_range.high)
    return Account(address, balance)


def generate_many(arguments):
    count = arguments.count
    address_range = AddressRange.get_range(arguments.address_range)
    value_range = ValueRange.get_range(arguments.value_range)

    accounts = []
    existing_addresses = set()
    for i in range(count):
        account = generate_account(address_range, value_range, existing_addresses)
        accounts.append(account)
        existing_addresses.add(account.address)

    # accounts = [
    #     Account(2**79 + 2**16, int(2e18)),
    #     Account(2 ** 16, int(1e18)),
    #     Account(0, 0),
    #     Account(19, 1256),
    # ]
    # print(accounts)

    tree_builder = TopDownBuilder(accounts)
    tree_root = tree_builder.build()
    # print(tree_root.print(0))
    print("Total value", sum([account.balance for account in accounts]))
    print("Merkle tree root", tree_root.print_hash(tree_root.hash()))

    return {
        'accounts': [
            { "address": account.address, "balance": account.balance}
            for account in accounts
        ],
        "merkle_tree_root": {
            "high": int.from_bytes(tree_root.hash()[:16], 'big', signed=False),
            "low": int.from_bytes(tree_root.hash()[16:32], 'big', signed=False)
        }
    }

def generate_single(arguments):
    address_range = AddressRange.get_range(arguments.address_range)
    value_range = ValueRange.get_range(arguments.value_range)
    # account = generate_account(address_range, value_range, set())
    account = Account(2**79 + 2**16, int(2e18))
    print(account)

    hash = account_keccak(account)
    print(hash)
    hash_int = int.from_bytes(hash, 'big', signed=False)
    print(hash_int)

    return {
        'account': { "address": account.address, "balance": account.balance},
        "account_hash": {
            # big endian = high bytes first, so :16 is the "high" 16-byte word in a 32-byte hash
            "high": int.from_bytes(hash[:16], 'big', signed=False),
            "low": int.from_bytes(hash[16:32], 'big', signed=False)
        }
    }

DESTINATION_FOLDER = "."

def main():
    arguments = ArgumentParser().parse_args()
    if arguments.single:
        data = generate_single(arguments)
        destination_file = os.path.join(DESTINATION_FOLDER, "single_input.json")
    else:
        data = generate_many(arguments)
        destination_file = os.path.join(DESTINATION_FOLDER, "balance_sum_prover.json")

    to_write = json.dumps(data, indent=4, sort_keys=True)
    with open(destination_file, "wb") as file:
        file.write(to_write.encode())

if __name__ == "__main__":
    main()