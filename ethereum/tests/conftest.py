import contextlib

import pytest
from brownie import accounts, NodeOperatorRegistry, TVLOracle, MockFactRegistry

from merkle import merkle_tree


@pytest.fixture(scope='module')
def node_operator_contract_admin(accounts):
    return accounts[0]


@pytest.fixture(scope='module')
def node_operator_registry(node_operator_contract_admin, NodeOperatorRegistry):
    return NodeOperatorRegistry.deploy(node_operator_contract_admin, {'from': node_operator_contract_admin})


@pytest.fixture(scope='module')
def cairo_program_hash():
    hash_bytes = b'\x00' * 32
    return int.from_bytes(hash_bytes, 'big', signed=False)


@pytest.fixture(scope='module')
def fact_registry(node_operator_contract_admin):
    return MockFactRegistry.deploy({'from': node_operator_contract_admin})


@pytest.fixture(scope='module')
def tvl_oracle(node_operator_contract_admin, cairo_program_hash, fact_registry, node_operator_registry, TVLOracle):
    deploy_tx_info = {"from": node_operator_contract_admin}
    return TVLOracle.deploy(
        node_operator_contract_admin, cairo_program_hash, fact_registry.address, node_operator_registry.address,
        deploy_tx_info
    )


class ProgressiveMerkleTreeBuilderContextManager(contextlib.AbstractContextManager):
    def __self__(self):
        self._current = None

    def __enter__(self):
        self._current = merkle_tree.ProgressiveMerkleTreeBuilder()
        return self._current

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._current = None


@pytest.fixture(scope='function')
def progressive_merkle_tree_builder():
    return merkle_tree.ProgressiveMerkleTreeBuilder()


@pytest.fixture(scope='module')
def progressive_merkle_tree_builder_mgr():
    return ProgressiveMerkleTreeBuilderContextManager()
