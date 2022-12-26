from brownie.test import given
from hypothesis import strategies as st
from strategies import pubkeys
from utils import IntUtils

class TestTVLOracle:
    @given(low_bytes=st.binary(min_size=16, max_size=16), high_bytes=st.binary(min_size=16, max_size=16))
    def test_reconstruct_uint_from_program_output(self, tvl_oracle, low_bytes, high_bytes):
        high = int.from_bytes(high_bytes, 'big', signed=False)
        low = int.from_bytes(low_bytes, 'big', signed=False)
        expected_hash_hex = IntUtils.read_pair_into_hex_str(high, low)
        actual = tvl_oracle.reconstruct_keccak_from_program_output(high, low)
        assert actual == expected_hash_hex
