from dataclasses import dataclass

from typing import List, TypedDict
import logging
from eth_typing import HexStr

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

    def __init__(self, beacon_state: BeaconState, lido_operator_keys: List[HexStr]):
        self.beacon_state = beacon_state
        self.lido_operator_keys = lido_operator_keys

    @property
    def lido_operators_in_eth(self):
        validators = [
            self.beacon_state.find_validator(key)
            for key in self.lido_operator_keys
        ]
        return [
            validator for validator in validators if validator is not None
        ]

    @property
    def lido_tlv(self) -> int:
        return sum(validator.balance for validator in self.lido_operators_in_eth)

    def to_cairo(self) -> ProverPayloadSerialized:
        return ProverPayloadSerialized(
            beacon_state=self.beacon_state.to_cairo(),
            validator_keys=self.lido_operator_keys,
        )

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"ProverPayload(beacon_state={self.beacon_state}, lido_operator_keys={self.lido_operator_keys}, " \
               f"lido_tlv={self.lido_tlv}"


class ProverOutput:
    def __init__(self, raw_output: List[int]):
        assert len(raw_output) == 5, \
            """
            Output should include:
            * Beacon state Merkle Tree Root (2 lines)
            * Validator keys Merkle Tree Root (2 lines)
            * Total Value Locked (1 line)
            """
        self.beacon_state_mtr = IntUtils.read_pair_into_hex_str(raw_output[0], raw_output[1])
        self.validator_keys_mtr = IntUtils.read_pair_into_hex_str(raw_output[2], raw_output[3])
        self.total_value_locked = raw_output[4]
        self.raw_output = raw_output

    @classmethod
    def read_from_prover_output(cls, prover_output: List[int]) -> 'ProverOutput':
        return cls(prover_output)

    def __str__(self):
        return f"ProverOutput(beacon_state_mtr={self.beacon_state_mtr}, validator_keys_mtr={self.validator_keys_mtr}, " \
               f"total_value_locked={self.total_value_locked})"
