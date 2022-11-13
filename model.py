from decimal import Decimal

import logging
from eth_typing import HexStr

from backports import TypedDict
from api.eth_api import BeaconState, BeaconStateCairoSerialized
from api.lido_api import LidoOperatorList, OperatorKeysCairoSerialized

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
