import logging
import json
import os

import config

from api.eth_api import get_web3_connection, CachedBeaconAPIWrapper, BeaconState, BeaconAPIWrapper
from api.lido_api import CachedLidoWrapper, LidoOperatorList, LidoWrapper
from disk_cache.json_protocol import CustomJsonEncoder

from web3.beacon import Beacon

from model import ProverPayload

DESTINATION_FOLDER = "."

LOGGER = logging.getLogger(__name__)


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


def main():
    beacon_state = get_beacon_state()
    lido_operator_keys = get_lido_operator_keys()
    prover_payload = ProverPayload(beacon_state, lido_operator_keys)

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