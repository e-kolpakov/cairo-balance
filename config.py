import json

with open('config.json') as json_file:
    raw_config = json.load(json_file)

LOG_LEVEL = 'DEBUG'

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
    'loggers': {},
    'root': {
        'level': LOG_LEVEL,
        'handlers': ['console']
    },
}

from logging import config

config.dictConfig(LOGGER_CONFIG)

WEB3_API =  raw_config["web3_api"]
WEB3_GOERLI_API =  raw_config["web3_goerli_api"]
ETH2_API =  raw_config["eth2_api"]
ETH2_PRATER_API =  raw_config["eth2_prater_api"]
WEB3_CACHE_LOCATION = "./cache/web3"
LIDO_CACHE_LOCATION = "./cache/lido"
ETH2_CACHE_LOCATION = "./cache/eth2"