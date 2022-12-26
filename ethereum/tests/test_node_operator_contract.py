from brownie.test import given
from hypothesis import strategies as st
from strategies import pubkeys
from utils import IntUtils


class TestNodeOperatorRegistryInitialState:
    def test_zerohashes(self, node_operator_registry, progressive_merkle_tree_builder):
        expected_zerohashes = [
            node.hash_hex()
            for node in progressive_merkle_tree_builder.zerohashes
        ]

        actual_zerohashes = node_operator_registry.get_zerohashes()
        assert len(expected_zerohashes) == len(actual_zerohashes)
        for (idx, (actual, expected)) in enumerate(zip(actual_zerohashes, expected_zerohashes)):
            assert actual == expected, f"Not equal at idx {idx}: {actual} != {expected}"

    def test_merkle_tree_root(self, node_operator_registry, progressive_merkle_tree_builder):
        expected = progressive_merkle_tree_builder.build().hash_hex()
        actual = node_operator_registry.get_keys_root()
        assert actual == expected


class TestNodeOperatorRegistry:
    @given(keys=st.lists(pubkeys, max_size=100, unique=True))
    def test_zerohashes(self, node_operator_registry, progressive_merkle_tree_builder_mgr, keys):
        with progressive_merkle_tree_builder_mgr as tree_builder:
            for key_bytes in keys:
                tree_builder.add_values(IntUtils.pubkey_bytes_to_keccak_input(key_bytes))
            expected = tree_builder.build().hash_hex()
        for key in keys:
            node_operator_registry.add_key(key)
        actual = node_operator_registry.get_keys_root()
        assert actual == expected