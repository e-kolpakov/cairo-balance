from decimal import Decimal

import logging

import enum
import json
import os
import random
import sys
import argparse
from eth_typing import HexStr
from lido_sdk.methods.typing import OperatorKey
from typing import TypeVar, Set

from tap import Tap

from eth_api import BeaconState, Validator
from input_from_eth import read_from_eth, ProverPayload
from json_protocol import CustomJsonEncoder
from lido_api import LidoOperatorList, OperatorKeyAdapter
from merkle_tree import TopDownBuilder

T = TypeVar('T')

LOGGER = logging.getLogger(__name__)

class GenerationMode(enum.Enum):
    STUB = 'stub'
    GEN = "gen"
    FROM_ETH = 'from_eth'

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
            return cls(0, 2**160)
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
    mode: GenerationMode

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
            "-m", "--mode", action=EnumAction, type=GenerationMode,
            default=GenerationMode.STUB
        )


def generate_many(arguments):
    pass
    # count = arguments.count
    # address_range = AddressRange.get_range(arguments.address_range)
    # value_range = ValueRange.get_range(arguments.value_range)
    #
    # accounts = []
    # existing_addresses = set()
    # for i in range(count):
    #     account = generate_account(address_range, value_range, existing_addresses)
    #     accounts.append(account)
    #     existing_addresses.add(account.address)
    #
    # tree_builder = TopDownBuilder(accounts)
    # tree_root = tree_builder.build()
    # # print(tree_root.print(0))
    # print(f"Total value {sum([account.balance for account in accounts])} wei" )
    # print("Merkle tree root", tree_root.print_hash(tree_root.hash()))
    #
    # return {
    #     'accounts': [
    #         { "address": f"0x{account.address:020x}", "balance": account.balance}
    #         for account in accounts
    #     ],
    #     "merkle_tree_root": {
    #         "high": int.from_bytes(tree_root.hash()[:16], 'big', signed=False),
    #         "low": int.from_bytes(tree_root.hash()[16:32], 'big', signed=False)
    #     }
    # }

def stub():
    key1 = 0x1
    key2 = 0x968ff4505567afa998c734bc85b73e7fd8f1003650af5f47371367cf83cb534dca970234bc96696a91b232e90e173350

    key3 = 0x3
    prover = ProverPayload(
        beacon_state=BeaconState(
            [
                Validator(HexStr(f"{key1:#096x}"), Decimal(1000)),
                Validator(HexStr(f"{key2:#096x}"), Decimal(2000)),
                Validator(HexStr(f"{key3:#096x}"), Decimal(4000)),
            ]
        ),
        lido_operators=LidoOperatorList(
            [
                OperatorKeyAdapter(
                    operator_key=OperatorKey(
                        index=0, operator_index=0, key=key1.to_bytes(48, 'big', signed=False), depositSignature=b'asdfgh', used=True
                    )
                ),
                OperatorKeyAdapter(
                    operator_key=OperatorKey(
                        index=1, operator_index=0, key=key2.to_bytes(48, 'big', signed=False), depositSignature=b'qweasd', used=True
                    )
                )
            ]
        )
    )
    return prover.to_cairo()

def generate(arguments):
    pass

def from_eth():
    prover_payload = read_from_eth()
    LOGGER.info("Generated prover payload %s", prover_payload)
    LOGGER.debug("Serializing payload to json")
    return prover_payload.to_cairo()

DESTINATION_FOLDER = "."

def main():
    arguments = ArgumentParser().parse_args()
    destination_file = os.path.join(DESTINATION_FOLDER, "balance_sum_prover.json")
    if arguments.mode == GenerationMode.STUB:
        data = stub()
    elif arguments.mode == GenerationMode.GEN:
        raise ValueError(f"Generation mode {arguments.mode} is yet unsupported")
        # data = generate(arguments)
    elif arguments.mode == GenerationMode.FROM_ETH:
        data = from_eth()
    else:
        raise ValueError(f"Unsupported generation mode {arguments.mode}")

    to_write = json.dumps(data, indent=4, sort_keys=True, cls=CustomJsonEncoder)
    with open(destination_file, "wb") as file:
        file.write(to_write.encode())

if __name__ == "__main__":
    main()