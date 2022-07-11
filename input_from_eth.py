import json
import os
from typing import TypeVar

from account import Account
from merkle_tree import TopDownBuilder
from web3 import Web3, EthereumTesterProvider
from eth_tester import EthereumTester

T = TypeVar('T')
DESTINATION_FOLDER = "."

ADDRESSES = EthereumTester().get_accounts()


def get_web3_connection():
    # ETH_ENDPOINT = 'https://cloudflare-eth.com'
    # eth_connection = Web3(HTTPProvider(ETH_ENDPOINT))
    return Web3(EthereumTesterProvider())

def read_from_eth():
    accounts = []
    connection = get_web3_connection()
    for address in ADDRESSES:
        balance = connection.eth.get_balance(address)
        accounts.append(Account(int(address, 0), balance))

    tree_builder = TopDownBuilder(accounts)
    tree_root = tree_builder.build()
    # print(tree_root.print(0))
    print("Total value", sum([account.balance for account in accounts]))
    print("Merkle tree root", tree_root.print_hash(tree_root.hash()))

    return {
        'accounts': [
            { "address": account.address, "balance": account.balance}
            for account in accounts
        ],
        "merkle_tree_root": {
            "high": int.from_bytes(tree_root.hash()[:16], 'big', signed=False),
            "low": int.from_bytes(tree_root.hash()[16:32], 'big', signed=False)
        }
    }


def main():
    data = read_from_eth()
    to_write = json.dumps(data, indent=4, sort_keys=True)
    destination_file = os.path.join(DESTINATION_FOLDER, "balance_sum_prover.json")
    with open(destination_file, "wb") as file:
        file.write(to_write.encode())

if __name__ == "__main__":
    main()