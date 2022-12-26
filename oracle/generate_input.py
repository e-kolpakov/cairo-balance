from hashlib import sha256

from decimal import Decimal

import logging

import enum
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

    def sample(self, count: int, unique=False) -> Iterator[int]:
        if self.size < sys.maxsize:
            if unique:
                yield from random.sample(range(self._low, self._high), count)
            else:
                yield from random.choices(range(self._low, self._high), k=count)
        else:
            # doing the above would result in OverflowError: Python int too large to convert to C ssize_t
            if unique:
                assert count < (self.size // 100), "too many values to generate - " \
                                                   "cannot guarantee generating unique values efficiently"
            seen = set()
            for _idx in range(count):
                should_generate = True
                while should_generate:
                    new_val = random.randint(self._low, self._high)
                    if unique:
                        should_generate = new_val in seen
                        seen.add(new_val)
                    else:
                        should_generate = False
                    yield new_val


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


def stub() -> (BeaconState, LidoOperatorList):
    key1 = 0x1
    key2 = 0x968ff4505567afa998c734bc85b73e7fd8f1003650af5f47371367cf83cb534dca970234bc96696a91b232e90e173350

    key3 = 0x3
    beacon_state=BeaconState(
        [
            Validator(HexStr(f"{key1:#096x}"), Decimal(1000)),
            Validator(HexStr(f"{key2:#096x}"), Decimal(2000)),
            Validator(HexStr(f"{key3:#096x}"), Decimal(4000)),
        ]
    )
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
    return (beacon_state, lido_operators)


def generate(
        address_range_mode: RangeMode, value_range_mode: RangeMode, count_eth: int, count_lido: int
) -> (BeaconState, LidoOperatorList):
    assert count_eth >= count_lido, "Eth count must be greater or equal than lido_count"
    address_range = AddressRange.get_range(address_range_mode)
    value_range = AddressRange.get_range(value_range_mode)
    unique_addresses = list(address_range.sample(count_eth, unique=True))
    balances = list(value_range.sample(count_eth))
    lido_operator_keys = random.sample(unique_addresses, count_lido)

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
    return (beacon_state, lido_operators)
