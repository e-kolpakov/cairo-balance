from dataclasses import dataclass

from typing import List
import logging
from eth_typing import HexStr

from backports import TypedDict
from api.eth_api import BeaconState, BeaconStateCairoSerialized
from api.lido_api import LidoOperatorList, OperatorKeysCairoSerialized
from utils import IntUtils

DESTINATION_FOLDER = "."

LOGGER = logging.getLogger(__name__)

class ProverPayloadSerialized(TypedDict):
    beacon_state: BeaconStateCairoSerialized
    # beacon_state_mtr: HexStr
    validator_keys: OperatorKeysCairoSerialized
    # validator_keys_mtr: HexStr
    # total_value_locked: int

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
        return {
            "beacon_state": self.beacon_state.to_cairo(),
            "validator_keys": self.lido_operators.to_cairo(),
        }

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        self.LOGGER.debug("Calling __str__")
        return f"ProverPayload(beacon_state={self.beacon_state}, lido_operators={self.lido_operators}, lido_tlv={self.lido_tlv}"

@dataclass
class ProverOutput:
    beacon_state_mtr: HexStr
    validator_keys_mtr: HexStr
    total_value_locked: int

    @classmethod
    def read_from_prover_output(cls, prover_output: List[int]) -> 'ProverOutput':
        assert len(prover_output) == 5, \
            """
            Output should include:
            * Beacon state Merkle Tree Root (2 lines)
            * Validator keys Merkle Tree Root (2 lines)
            * Total Value Locked (1 line)
            """
        beacon_state_mtr = IntUtils.read_pair_into_hex_str(prover_output[0], prover_output[1])
        validator_keys_mtr = IntUtils.read_pair_into_hex_str(prover_output[2], prover_output[3])
        total_value_locked = prover_output[4]
        return cls(beacon_state_mtr, validator_keys_mtr, total_value_locked)