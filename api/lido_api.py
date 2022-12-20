from dataclasses import dataclass

from eth_typing import HexStr
from typing import List, Any, Dict, Generator, Iterator
from backports import Literal

from lido_sdk.methods.typing import OperatorKey

import config
import logging

from web3 import Web3

from disk_cache.cache import TypedJsonDiskCache
from api.eth_api import get_web3_connection
from lido_sdk import Lido

from keccak_utils import KeccakInput
from merkle.merkle_tree import MerkleTreeNode, ProgressiveMerkleTreeBuilder
from utils import IntUtils, ByteEndianness, BytesUtils

OperatorKeyAttributes = Literal['index', 'operator_index', 'key', 'depositSignature', 'used']
OperatorKeysCairoSerialized = List[HexStr]

class OperatorKeyAdapter:
    """
    Adapter over lido_sdk OPeratorKey, mainly to make working with keys more convenient
    """
    def __init__(self, operator_key: OperatorKey):
        self._operator_key = operator_key

    def _decode_hex(self, raw: bytes, endianness: ByteEndianness = 'big', signed=False) -> int:
        return int.from_bytes(self._operator_key["key"], endianness, signed=signed)

    def _maybe_pad(self, value: bytes, padding=False):
        if not padding:
            return value
        else:
            return BytesUtils.pad_to_32_multiple(value)

    @property
    def key_bytes(self):
        return self._operator_key["key"]

    @property
    def key(self) -> HexStr:
        return IntUtils.to_hex_str(self._decode_hex(self._operator_key["key"]))

    def key_int(self) -> int:
        return self._decode_hex(self._operator_key["key"])

    @property
    def deposit_signature(self):
        return self._decode_hex(self._operator_key["depositSignature"])

    def __getattr__(self, name: OperatorKeyAttributes):
        return self._operator_key[name]

    def __repr__(self):
        return f"OperatorKeyAdapter(key={self.key}, signature={self.deposit_signature:#x})"


@dataclass
class LidoOperatorList:
    LOGGER = logging.getLogger(__name__ + ".LidoOperatorList")
    operators: List[OperatorKeyAdapter]

    def _flatten(self) -> Iterator[KeccakInput]:
        for operator in self.operators:
            yield from IntUtils.pubkey_to_keccak_input(operator.key_int())

    # @functools.cached_property - TODO: this is not avaialble in python 3.7
    def merkle_tree_root(self) -> MerkleTreeNode:
        tree_builder = ProgressiveMerkleTreeBuilder()
        tree_builder.add_values(self._flatten())
        return tree_builder.build()

    def to_cairo(self):
        return [operator.key for operator in self.operators]

    @property
    def total_operators(self):
        return len(self.operators)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        self.LOGGER.debug("Calling __str__")
        return f"LidoOperatorList(total_operators={self.total_operators}, first_10_operators={self.operators[:10]}"


class OperatorKeyJsonableSerializer:
    @classmethod
    def _hex_str_to_bytes(cls, value: HexStr, length: int, endianness: ByteEndianness = 'big', signed: bool = False):
        return IntUtils.from_hex_str(value).to_bytes(length, endianness, signed=signed)

    @classmethod
    def serialize(self, operator_key: OperatorKeyAdapter):
        return {
            "index": operator_key.index,
            "operator_index": operator_key.operator_index,
            "key": operator_key.key_hex,
            "depositSignature": IntUtils.to_hex_str(operator_key.deposit_signature),
            "used": operator_key.used,
        }

    @classmethod
    def deserialize(cls, json_dict: Dict[str, Any]) -> OperatorKeyAdapter:
        operator_key = OperatorKey(
            index=json_dict["index"],
            operator_index=json_dict["operator_index"],
            key=cls._hex_str_to_bytes(json_dict["key"], 80),
            depositSignature=cls._hex_str_to_bytes(json_dict["depositSignature"], 80),
            used=json_dict["used"],
        )
        return OperatorKeyAdapter(operator_key)

class LidoWrapper:
    def __init__(self, w3: Web3):
        self._lido_api = Lido(w3)

    def get_operator_keys(self) -> List[OperatorKeyAdapter]:
        operator_indexes = self._lido_api.get_operators_indexes()
        operators_data = self._lido_api.get_operators_data(operator_indexes)
        operator_keys = self._lido_api.get_operators_keys(operators_data)
        return [
            OperatorKeyAdapter(operator_key)
            for operator_key in operator_keys
        ]


class CachedLidoWrapper(LidoWrapper):
    LOGGER = logging.getLogger(__name__ + ".CachedLidoWrapper")
    def __init__(self, w3: Web3):
        super(CachedLidoWrapper, self).__init__(w3)
        self._validator_cache: TypedJsonDiskCache[OperatorKeyAdapter] = TypedJsonDiskCache(
            config.LIDO_CACHE_LOCATION,
            OperatorKeyJsonableSerializer.deserialize,
            OperatorKeyJsonableSerializer.serialize
        )

    def get_operator_keys(self) -> List[OperatorKeyAdapter]:
        self.LOGGER.info("Fetching Lido validators")
        cache_key = ['lido_validators']
        cached = list(self._validator_cache.read_model(*cache_key))
        if cached:
            self.LOGGER.debug("Found validators in json disk cache")
            return cached

        self.LOGGER.debug("Json disk cache is empty")
        read_from_api = super(CachedLidoWrapper, self).get_operator_keys()
        self.LOGGER.debug(f"Saving {len(read_from_api)} validators into json disk cache")
        self._validator_cache.save_models(read_from_api, *cache_key)
        return read_from_api

def main():
    w3 = get_web3_connection(config.WEB3_API)
    lido_wrapper = CachedLidoWrapper(w3)
    operator_keys = lido_wrapper.get_operator_keys()
    print(len(operator_keys))
    print(operator_keys[:10])


if __name__ == "__main__":
    main()