from brownie import accounts, NodeOperatorRegistry


def main():
    owner = accounts[0]
    deployment = NodeOperatorRegistry.deploy(owner, {'from': owner})
    key = 1
    key_bytes = key.to_bytes(48, 'big')

    tx = deployment.add_key(key_bytes)
    print("events", tx.events)
    print("mtr", deployment.get_keys_root())