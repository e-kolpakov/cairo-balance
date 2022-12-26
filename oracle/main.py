import enum
import argparse
import logging
from typing import List, Callable, Tuple

from eth_typing import HexStr
from tap import Tap

import config
import generate_input

from api.eth_api import get_web3_connection, CachedBeaconAPIWrapper, BeaconState, BeaconAPIWrapper
from api.lido_api import CachedLidoWrapper, LidoOperatorList, LidoWrapper
from web3.beacon import Beacon

from cairo import CairoInterface
from generate_input import RangeMode
from model import ProverPayload
from oracle import Oracle, StubTLVContract, ProverPayloadSource

DESTINATION_FOLDER = "."

LOGGER = logging.getLogger(__name__)


class DataSource(enum.Enum):
    STUB = 'stub'
    GEN = "gen"
    LIVE = 'live'


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
    source: DataSource

    bin_dir: str
    node_rpc_url: str

    count_eth: int
    count_lido: int
    address_range: RangeMode
    value_range: RangeMode

    store_input_copy: str
    submit: bool

    def configure(self):
        self.add_argument(
            "-s", "--source", action=EnumAction, type=DataSource,
            default=DataSource.STUB
        )
        # Cairo arguments
        self.add_argument(
            "--bin_dir", type=str,
            default="",
            help="The path to a directory that contains the cairo-compile and cairo-run scripts. "
                 "If not specified, files are assumed to be in the system's PATH.",
        )
        self.add_argument(
            "--node_rpc_url",
            type=str,
            default=config.WEB3_GOERLI_API,
            help="RPC URL to communicate with an Ethereum node on Goerli"
        )

        # Generation agruments
        self.add_argument(
            "-a", "--address_range", action=EnumAction, type=RangeMode,
            default=RangeMode.SMALL
        )
        self.add_argument(
            "-ce", "--count_eth", required=False, default=100,
            help="Number of ethereum validators to generate",
        )
        self.add_argument(
            "-cl", "--count_lido", required=False, default=20,
            help="Number of lido validators to generate",
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
            "--submit",
            action='store_true',
            default=False,
            help="Submit program to SHARP"
        )

        # debug arguments
        self.add_argument(
            "--store_input_copy",
            type=str,
            default=None,
            help="Write a copy of cairo program_input to this file. Default: do not write a copy"
        )


def assert_equal(label, python_mtr: str, cairo_mtr: str):
    if python_mtr != cairo_mtr:
        message = f"[Mismatch] [{label}]\nCairo :{cairo_mtr}\nPython:{python_mtr}"
        LOGGER.error(message)
        raise AssertionError(message)

class StaticProverPayloadSource(ProverPayloadSource):
    def __init__(self, input_source: Callable[[], Tuple[BeaconState, LidoOperatorList]]):
        beacon_state, lido_operator_list = input_source()
        self.beacon_state = beacon_state
        self.lido_operator_list = lido_operator_list

    def get_prover_payload(self):
        return ProverPayload(
            beacon_state=self.beacon_state,
            lido_operator_keys=[operator.key for operator in self.lido_operator_list.operators]
        )

class BlockchainProverPayloadSource:
    LOGGER = logging.getLogger(__name__ + ".BlockchainProverPayloadSource")
    def __init__(self, web3_enpoint, eth2_endpoint, use_cache=True):
        web3 = get_web3_connection(web3_enpoint)
        beacon = Beacon(eth2_endpoint)

        if use_cache:
            self.LOGGER.debug("Using read-through cache for Lido validators")
            lido_api = CachedLidoWrapper(web3)

            self.LOGGER.debug("Using read-through cache for beacon state")
            beacon_api = CachedBeaconAPIWrapper(beacon, config.ETH2_CACHE_LOCATION)
        else:
            lido_api = LidoWrapper(web3)
            beacon_api = BeaconAPIWrapper(beacon)

        self._lido_api = lido_api
        self._beacon_api = beacon_api

        self._beacon_state = None
        self._lido_operators_list = None
    @property
    def lido_operator_list(self) -> LidoOperatorList:
        if self._lido_operators_list is None:
            self.LOGGER.info("Fetching Lido validators")
            operator_keys = self._lido_api.get_operator_keys()
            self._lido_operators_list = LidoOperatorList(operator_keys)

        return self._lido_operators_list

    @property
    def beacon_state(self) -> BeaconState:
        if self._beacon_state is None:
            self.LOGGER.info("Fetching beacon state")
            all_eth_validators = self._beacon_api.validators()
            self._beacon_state = BeaconState(all_eth_validators)
        return self._beacon_state

    def get_prover_payload(self) -> (BeaconState, LidoOperatorList):
        beacon_state = self.beacon_state
        lido_operators = self.lido_operator_list
        return ProverPayload(
            beacon_state=beacon_state,
            lido_operator_keys=[operator.key for operator in lido_operators.operators]
        )


def main():
    args = ArgumentParser().parse_args()

    if args.source == DataSource.STUB:
        input_source = lambda: generate_input.stub()
        prover_payload_source = StaticProverPayloadSource(input_source)
    elif args.source == DataSource.GEN:
        input_source = lambda: generate_input.generate(args.address_range, args.value_range, args.count_eth, args.count_lido)
        prover_payload_source = StaticProverPayloadSource(input_source)
    elif args.source == DataSource.LIVE:
        prover_payload_source = BlockchainProverPayloadSource(config.WEB3_GOERLI_API, config.ETH2_API)
    else:
        raise ValueError(f"Unsupported generation mode {args.source}")

    LOGGER.debug("Creating Cairo interface")
    cairo_interface = CairoInterface(
        args.bin_dir, args.node_rpc_url, config.CairoApps.TLV_PROVER,
        serializer=lambda payload: payload.to_cairo(),
    )

    prover_payload = prover_payload_source.get_prover_payload()
    LOGGER.info("Prover payload %s", prover_payload)

    LOGGER.debug("Creating oracle instance")
    oracle = Oracle(prover_payload_source, cairo_interface, StubTLVContract(), dry_run=not args.submit)
    (parsed_output, _job_id, _fact_id) = oracle.run_oracle()

    LOGGER.info("Checking merkle tree roots and total value locked match")
    assert_equal(
        "BeaconState Merkle Tree Roots",
        prover_payload_source.beacon_state.merkle_tree_root().hash_hex(),
        parsed_output.beacon_state_mtr
    )
    assert_equal(
        "Validator Keys Merkle Tree Roots",
        prover_payload_source.lido_operator_list.merkle_tree_root().hash_hex(),
        parsed_output.validator_keys_mtr
    )
    assert_equal(
        "Total Value Locked",
        str(prover_payload.lido_tlv),
        str(parsed_output.total_value_locked)
    )
    print("MTRs and TLV matched - success")


if __name__ == "__main__":
    main()
