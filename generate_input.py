from hashlib import sha256

from decimal import Decimal

import logging

import enum
import json
import os
import random
import sys
from eth_typing import HexStr
from lido_sdk.methods.typing import OperatorKey
from typing import TypeVar, Set, Iterator

from api.eth_api import BeaconState, Validator
from api.lido_api import LidoOperatorList, OperatorKeyAdapter
from model import ProverPayload
from utils import IntUtils

T = TypeVar('T')

LOGGER = logging.getLogger(__name__)


class RangeMode(enum.Enum):
    SMALL = 'small'
    MEDIUM = 'medium'
    WIDE = 'wide'
    ETH = 'eth'
    UNRESTRICTED = 'unrestricted'


class EthereumConstants:
    TOTAL_SUPPLY = int(1e10)  # actually, ~100 times less, but it's only a matter of time (500 years at current rate)
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

    def sample_unique(self, count: int) -> Iterator[int]:
        return random.sample(range(self._low, self._high), count)

    def sample(self, count: int):
        return random.choices(range(self._low, self._high), k=count)


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
            return cls(0, 2 ** 160)
        elif mode == RangeMode.UNRESTRICTED:
            return cls(0, sys.maxsize)


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
    prover_payload = ProverPayload(
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
                        index=0, operator_index=0, key=key1.to_bytes(48, 'big', signed=False),
                        depositSignature=b'asdfgh', used=True
                    )
                ),
                OperatorKeyAdapter(
                    operator_key=OperatorKey(
                        index=1, operator_index=0, key=key2.to_bytes(48, 'big', signed=False),
                        depositSignature=b'qweasd', used=True
                    )
                )
            ]
        )
    )
    return prover_payload


def generate(
        address_range_mode: RangeMode, value_range_mode: RangeMode, eth_count: int, lido_count: int
) -> ProverPayload:
    assert eth_count >= lido_count, "Eth count must be greater or equal than lido_count"
    address_range = AddressRange.get_range(address_range_mode)
    value_range = AddressRange.get_range(value_range_mode)
    unique_addresses = list(address_range.sample_unique(eth_count))
    balances = list(value_range.sample(lido_count))
    lido_operator_keys = random.sample(unique_addresses, lido_count)

    validators = []
    for (key, balance) in zip(unique_addresses, balances):
        validator = Validator(IntUtils.to_hex_str(key), Decimal(balance))
        validators.append(validator)
    beacon_state = BeaconState(validators)

    operators = []
    for (index, key) in enumerate(lido_operator_keys):
        key_bytes = key.to_bytes(48, 'big')
        operator_key = OperatorKey(
            index=index, operator_index=index, key=key_bytes,
            depositSignature=sha256(key_bytes).digest(), used=True
        )
        operators.append(OperatorKeyAdapter(operator_key))
    lido_operators = LidoOperatorList(operators)
    return ProverPayload(beacon_state=beacon_state, lido_operators=lido_operators)

