from decimal import Decimal

import logging
import json
import os
from eth_typing import HexStr
from lido_sdk.methods.typing import OperatorKey

import config

from backports import TypedDict
from eth_api import get_web3_connection, CachedBeaconAPIWrapper, BeaconState, BeaconStateCairoSerialized, Validator
from json_protocol import CustomJsonEncoder
from lido_api import CachedLidoWrapper, LidoOperatorList, OperatorKeysCairoSerialized, OperatorKeyAdapter

from dataclasses import dataclass
from web3.beacon import Beacon

DESTINATION_FOLDER = "."

LOGGER = logging.getLogger(__name__)

class ProverPayloadSerialized(TypedDict):
    beacon_state: BeaconStateCairoSerialized
    beacon_state_mtr: HexStr
    validator_keys: OperatorKeysCairoSerialized
    validator_keys_mtr: HexStr
    total_value_locked: int

class ProverPayload:
    LOGGER = logging.getLogger(__name__ + ".ProverPayload")
    def __init__(self, beacon_state: BeaconState, lido_operators: LidoOperatorList):
        self.beacon_state = beacon_state
        self.lido_operators = lido_operators

    @property
    def lido_operators_in_eth(self):
        validators = [
            self.beacon_state.find_validator(operator.key)
            for operator in self.lido_operators.operators
        ]
        return [
            validator for validator in validators if validator is not None
        ]

    @property
    def lido_tlv(self) -> int:
        return sum(validator.balance for validator in self.lido_operators_in_eth)

    def to_cairo(self) -> ProverPayloadSerialized:
        beacon_state_merkle_tree = self.beacon_state.merkle_tree_root()
        validators_merkle_tree = self.lido_operators.merkle_tree_root()
        LOGGER.info("BeaconState merkle tree root %s", beacon_state_merkle_tree.hash_hex())
        LOGGER.info("LidoValidators merkle tree root %s", validators_merkle_tree.hash_hex())
        # print(beacon_state_merkle_tree.print(with_hash=True))
        # print(validators_merkle_tree.print(with_hash=True))
        return {
            "beacon_state": self.beacon_state.to_cairo(),
            "beacon_state_mtr": beacon_state_merkle_tree.to_cairo(),
            "validator_keys": self.lido_operators.to_cairo(),
            "validator_keys_mtr": validators_merkle_tree.to_cairo(),
            "total_value_locked": self.lido_tlv,
        }

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        self.LOGGER.debug("Calling __str__")
        return f"ProverPayload(beacon_state={self.beacon_state}, lido_operators={self.lido_operators}, lido_tlv={self.lido_tlv}"


def get_beacon_state() -> BeaconState:
    beacon = CachedBeaconAPIWrapper(Beacon(config.ETH2_API), config.ETH2_CACHE_LOCATION)
    all_eth_validators = beacon.validators()
    return BeaconState(all_eth_validators)


def get_lido_operator_keys() -> LidoOperatorList:
    w3 = get_web3_connection(config.WEB3_API)
    lido_wrapper = CachedLidoWrapper(w3)
    operator_keys = lido_wrapper.get_operator_keys()
    return LidoOperatorList(operator_keys)


def read_from_eth():
    beacon_state = get_beacon_state()
    lido_operator_keys = get_lido_operator_keys()
    prover_payload = ProverPayload(beacon_state, lido_operator_keys)
    LOGGER.debug("Gathered prover payload %s", prover_payload)
    return prover_payload

def main():
    prover_payload = read_from_eth()
    LOGGER.info("Generated prover payload %s", prover_payload)
    LOGGER.debug("Serializing payload to json")
    to_write = json.dumps(prover_payload.to_cairo(), indent=4, sort_keys=True, cls=CustomJsonEncoder)

    destination_file = os.path.join(DESTINATION_FOLDER, "balance_sum_prover.json")
    LOGGER.info("Writing prover payload to %s", destination_file)
    with open(destination_file, "wb") as file:
        file.write(to_write.encode())
    LOGGER.info("Written payload - proceeding")

if __name__ == "__main__":
    main()