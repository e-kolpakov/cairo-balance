import config
import logging

from dataclasses_json import DataClassJsonMixin
from typing import List

from dataclasses import dataclass
from decimal import Decimal

from web3 import Web3, HTTPProvider
from web3.beacon import Beacon

from cache import TypedJsonDiskCache
from merkle_tree import MerkleTreeRoot
from utils import AsDict


@dataclass
class Validator(DataClassJsonMixin, AsDict):
    pubkey: str
    balance: Decimal

    @classmethod
    def parse(cls, raw_data):
        # assert raw_data["validator"]["effective_balance"] == raw_data['balance']
        return cls(
            pubkey=raw_data["validator"]["pubkey"],
            balance=Decimal(int(raw_data["balance"])),
        )


def get_web3_connection(endpoint) -> Web3:
    return Web3(HTTPProvider(endpoint))


class BeaconWrapper:
    LOGGER = logging.getLogger(__name__ + ".BeaconWrapper")

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

    def calculate_merkle_tree(self) -> MerkleTreeRoot:
        pass


class CachedBeaconWrapper(BeaconWrapper):
    LOGGER = logging.getLogger(__name__ + ".CachedBeaconWrapper")

    def __init__(self, beacon: Beacon, storage_folder: str):
        super(CachedBeaconWrapper, self).__init__(beacon)
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
        read_from_api = super(CachedBeaconWrapper, self).validators()
        self.LOGGER.debug(f"Saving {len(read_from_api)} validators into json disk cache")
        self._validator_cache.save_models(read_from_api, *cache_key)
        return read_from_api

def main():
    beacon = CachedBeaconWrapper(Beacon(config.ETH2_API), config.ETH2_CACHE_LOCATION)
    validators = beacon.validators()
    print(len(validators))
    print(validators[:10])


if __name__ == "__main__":
    main()