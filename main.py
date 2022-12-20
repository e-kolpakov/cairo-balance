import enum
import argparse
import logging

from tap import Tap

import config
import generate_input

from api.eth_api import get_web3_connection, CachedBeaconAPIWrapper, BeaconState, BeaconAPIWrapper
from api.lido_api import CachedLidoWrapper, LidoOperatorList, LidoWrapper
from web3.beacon import Beacon

from cairo import CairoInterface
from generate_input import RangeMode
from model import ProverPayload, ProverOutput

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

        # debug arguments
        self.add_argument(
            "--store_input_copy",
            type=str,
            default=None,
            help="Write a copy of cairo program_input to this file. Default: do not write a copy"
        )


def get_beacon_state() -> BeaconState:
    LOGGER.info("Fetching beacon state")
    beacon = Beacon(config.ETH2_API)
    if config.USE_CACHE:
        LOGGER.debug("Using read-through cache for beacon state")
        beacon_api = CachedBeaconAPIWrapper(beacon, config.ETH2_CACHE_LOCATION)
    else:
        beacon_api = BeaconAPIWrapper(beacon)
    all_eth_validators = beacon_api.validators()
    return BeaconState(all_eth_validators)


def get_lido_operator_keys() -> LidoOperatorList:
    LOGGER.info("Fetching Lido validators")
    w3 = get_web3_connection(config.WEB3_API)
    if config.USE_CACHE:
        LOGGER.debug("Using read-through cache for Lido validators")
        lido_api = CachedLidoWrapper(w3)
    else:
        lido_api = LidoWrapper(w3)
    operator_keys = lido_api.get_operator_keys()
    return LidoOperatorList(operator_keys)


def get_live_prover_payload() -> ProverPayload:
    beacon_state = get_beacon_state()
    lido_operator_keys = get_lido_operator_keys()
    return ProverPayload(beacon_state, lido_operator_keys)


def assert_equal(label, python_mtr: str, cairo_mtr: str):
    if python_mtr != cairo_mtr:
        message = f"[Mismatch] [{label}]\nCairo :{cairo_mtr}\nPython:{python_mtr}"
        LOGGER.error(message)
        raise AssertionError(message)


def main():
    args = ArgumentParser().parse_args()

    if args.source == DataSource.STUB:
        prover_payload = generate_input.stub()
    elif args.source == DataSource.GEN:
        prover_payload = generate_input.generate(args.address_range, args.value_range, args.count_eth, args.count_lido)
    elif args.source == DataSource.LIVE:
        prover_payload = get_live_prover_payload()
    else:
        raise ValueError(f"Unsupported generation mode {args.source}")

    LOGGER.info("Generated prover payload %s", prover_payload)

    LOGGER.info("Creating Cairo interface")
    cairo_interface = CairoInterface(
        args.bin_dir, args.node_rpc_url, config.CairoApps.TLV_PROVER,
        serializer=lambda payload: payload.to_cairo(),
        cairo_path=config.PROJECT_ROOT
    )

    LOGGER.info("Running the program")
    cairo_output = cairo_interface.run(prover_payload, args.store_input_copy)
    LOGGER.debug(f"Raw cairo output {cairo_output}")

    LOGGER.info("Parsing cairo output")
    try:
        parsed_output = ProverOutput.read_from_prover_output(cairo_output)
    except AssertionError as e:
        LOGGER.exception("Couldn't parse cairo output:\n%s", cairo_output)
        raise
    LOGGER.debug("Cairo output %s", parsed_output)

    LOGGER.info("Checking merkle tree roots and total value locked match")
    assert_equal(
        "BeaconState Merkle Tree Roots",
        prover_payload.beacon_state.merkle_tree_root().hash_hex(),
        parsed_output.beacon_state_mtr
    )
    assert_equal(
        "Validator Keys Merkle Tree Roots",
        prover_payload.lido_operators.merkle_tree_root().hash_hex(),
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
