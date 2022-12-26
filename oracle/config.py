import os.path

import json

PROJECT_ROOT = os.path.dirname(__file__)

CONFIG_LOCATION = os.path.join(PROJECT_ROOT, 'config.json')
CAIRO_CODE_LOCATION = os.path.join(PROJECT_ROOT, 'cairo')
INTEGRATION_TESTS = os.path.join(PROJECT_ROOT, 'integration_test')

with open(CONFIG_LOCATION) as json_file:
    raw_config = json.load(json_file)

LOG_LEVEL = 'DEBUG'

NOISY_LOGGERS = {
    'disk_cache.JsonDiskCache': 'INFO',
    'integration_test.testutils.CairoTestHelper': 'INFO',
    'urllib3': 'INFO',
    'web3': 'INFO'
}

LOGGER_CONFIG = {
    'version': 1,
    'formatters': {
        'detailed': {
            'class': 'logging.Formatter',
            'format': '%(asctime)s %(name)-30s %(levelname)-8s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': LOG_LEVEL,
            "formatter": "detailed"
        },
        # 'file': {
        #     'class': 'logging.FileHandler',
        #     'filename': 'mplog.log',
        #     'mode': 'w',
        #     'formatter': 'detailed',
        # }
    },
    'loggers': {
        logger: {
            'level': level,
            'handlers': ['console']
        } for logger, level in NOISY_LOGGERS.items()
    },
    'root': {
        'level': LOG_LEVEL,
        'handlers': ['console']
    },
}

from logging import config

config.dictConfig(LOGGER_CONFIG)

WEB3_API =  raw_config["web3_api"]
WEB3_GOERLI_API =  raw_config["web3_goerli_api"]
WEB3_LOCAL_API = "127.0.0.1:8545"
ETH2_API =  raw_config["eth2_api"]
ETH2_PRATER_API =  raw_config["eth2_prater_api"]
WEB3_CACHE_LOCATION = "./cache/web3"
LIDO_CACHE_LOCATION = "./cache/lido"
ETH2_CACHE_LOCATION = "./cache/eth2"
USE_CACHE = True
# DEBUG = True
DEBUG = False

class CairoApps:
    MERKLE_TREE = os.path.join(CAIRO_CODE_LOCATION, 'merkle_tree.cairo')
    TLV_PROVER = os.path.join(CAIRO_CODE_LOCATION, 'tlv_prover.cairo')

    class IntegrationTests:
        ZEROHASHES = os.path.join(INTEGRATION_TESTS, 'zerohashes_check.cairo')
        MERKLE_TREE = os.path.join(INTEGRATION_TESTS, 'merkle_tree_check.cairo')
        MERKLE_TREE_LEAVES = os.path.join(INTEGRATION_TESTS, 'mtr_leaves_check.cairo')
        BEACON_STATE = os.path.join(INTEGRATION_TESTS, 'beacon_state_check.cairo')
