import functools

from eth_typing import HexStr

import config
import logging

from dataclasses_json import DataClassJsonMixin
from typing import List, Dict, Optional, Generator, Iterator
from backports import TypedDict

from dataclasses import dataclass
from decimal import Decimal

from web3 import Web3, HTTPProvider
from web3.beacon import Beacon

from disk_cache.cache import TypedJsonDiskCache
from keccak_utils import KeccakInput
from merkle.merkle_tree import MerkleTreeNode, ProgressiveMerkleTreeBuilder
from utils import AsDict, IntUtils


class ValidatorCairoSerialized(TypedDict):
    pubkey: str
    balance: Decimal

BeaconStateCairoSerialized = Dict[str, List[ValidatorCairoSerialized]]


@dataclass
class Validator(DataClassJsonMixin, AsDict):
    pubkey: HexStr
    balance: Decimal

    @classmethod
    def parse(cls, raw_data):
        # assert raw_data["validator"]["effective_balance"] == raw_data['balance']
        return cls(
            pubkey=HexStr(raw_data["validator"]["pubkey"]),
            balance=Decimal(int(raw_data["balance"])),
        )

    def to_cairo(self) -> ValidatorCairoSerialized:
        return {"pubkey": self.pubkey, "balance": self.balance}

    @property
    def pubkey_int(self) -> int:
        return int(self.pubkey, 16)

    @property
    def balance_int(self) -> int:
        return int(self.balance)


@dataclass
class BeaconState:
    LOGGER = logging.getLogger(__name__ + ".BeaconState")
    validators: List[Validator]
    
    def __init__(self, validators):
        self.validators = validators
        self._validator_lookup = {int(validator.pubkey, 16): validator for validator in validators}

    def find_validator(self, pubkey: HexStr) -> Optional[Validator]:
        return self._validator_lookup.get(int(pubkey, 16))

    def _flatten(self) -> Iterator[KeccakInput]:
        """
        MerkleTree needs the input to be a list of `bytes` or `bytearray`s
        This function "flattens" the BeaconState to that shape

        Note: "layout" matters - if order of fields is changed, the hash will be different
        :return:
        """
        for validator in self.validators:
            yield from IntUtils.pubkey_to_keccak_input(validator.pubkey_int)
            yield IntUtils.to_keccak_input(validator.balance_int, size_hint=32)

    def merkle_tree_builder(self) -> ProgressiveMerkleTreeBuilder:
        tree_builder = ProgressiveMerkleTreeBuilder()
        tree_builder.add_values(self._flatten())
        return tree_builder

    # @functools.cached_property - TODO: this is not available in python 3.7
    def merkle_tree_root(self) -> MerkleTreeNode:
        return self.merkle_tree_builder().build()

    def to_cairo(self) -> BeaconStateCairoSerialized:
        return {
            "validators": [
                validator.to_cairo()
                for validator in self.validators
            ]
        }
    @property
    def total_validators(self):
        return len(self.validators)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        self.LOGGER.debug("Calling __str__")
        return f"BeaconState(total_validators={self.total_validators}, first_10_validators={self.validators[:10]}"


def get_web3_connection(endpoint) -> Web3:
    return Web3(HTTPProvider(endpoint))


class BeaconAPIWrapper:
    LOGGER = logging.getLogger(__name__ + ".BeaconAPIWrapper")

    def __init__(self, beacon: Beacon):
        self._beacon = beacon

    def validators(self, state='head') -> List[Validator]:
        self.LOGGER.info("Fetching validators from ETH2 node")
        raw_data = self._beacon.get_validators(state_id=state)
        self.LOGGER.info("Validators fetched, parsing")
        return [
            Validator.parse(raw_record)
            for raw_record in raw_data["data"]
        ]

class CachedBeaconAPIWrapper(BeaconAPIWrapper):
    LOGGER = logging.getLogger(__name__ + ".CachedBeaconAPIWrapper")

    def __init__(self, beacon: Beacon, storage_folder: str):
        super(CachedBeaconAPIWrapper, self).__init__(beacon)
        self._validator_cache: TypedJsonDiskCache[Validator] = TypedJsonDiskCache(
            config.ETH2_CACHE_LOCATION, Validator.from_dict, Validator.to_dict
        )

    def validators(self, state='head') -> List[Validator]:
        self.LOGGER.info("Fetching ETH2 validators")
        cache_key = ['validators', state]
        cached = list(self._validator_cache.read_model(*cache_key))
        if cached:
            self.LOGGER.debug("Found validators in json disk cache")
            return cached

        self.LOGGER.debug("Json disk cache is empty")
        read_from_api = super(CachedBeaconAPIWrapper, self).validators()
        self.LOGGER.debug(f"Saving {len(read_from_api)} validators into json disk cache")
        self._validator_cache.save_models(read_from_api, *cache_key)
        return read_from_api

def main():
    beacon = CachedBeaconAPIWrapper(Beacon(config.ETH2_API), config.ETH2_CACHE_LOCATION)
    validators = beacon.validators()
    print(len(validators))
    print(validators[:10])


if __name__ == "__main__":
    main()