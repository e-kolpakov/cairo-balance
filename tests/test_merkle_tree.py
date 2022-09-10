from typing import List

import unittest

import ddt

from eth_progressive_merkle_tree_reference_impl import testdata, branch_by_branch
import merkle_tree

from hypothesis import strategies as st, given, note, settings, example

from utils import IntUtils

keccak_hash = st.binary(min_size=32, max_size=32)

common_test_cases = [
    [],
    testdata[:1],
    testdata[:2],
    testdata[:3],
    testdata[:5],
    testdata[:256],
    testdata[:5049]
]

def get_merkle_tree_from_eth_builder(input_data):
    tree = merkle_tree.EthereumBuilder()
    tree.add_values(input_data)
    return tree.build().hash()


@ddt.ddt
class TestEthereumBuilder(unittest.TestCase):
    @ddt.data(*common_test_cases)
    def test_trees_match(self, test_data):
        actual = get_merkle_tree_from_eth_builder(test_data)
        reference_impl_result = branch_by_branch(test_data)
        self.assertEqual(actual, reference_impl_result)


class TestHypothesisEthereumBuilder(unittest.TestCase):
    def _pretty_print_input(self, test_data: List[bytes]):
        return [
            IntUtils.hex_str_from_bytes(test_record, 'big', signed=False)
            for test_record in test_data
        ]

    @given(st.lists(keccak_hash, max_size=2*16))
    def test_merkle_tree_root_matches(self, test_data):
        actual = get_merkle_tree_from_eth_builder(test_data)
        reference_impl_result = branch_by_branch(test_data)
        note(f"Input is {self._pretty_print_input(test_data)}")
        assert actual == reference_impl_result


if __name__ == "__main__":
    unittest.main()