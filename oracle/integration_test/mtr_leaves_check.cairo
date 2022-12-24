%builtins output range_check bitwise

from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.serialize import serialize_word
from starkware.cairo.common.alloc import alloc

from model import BeaconState, Validator, Eth2ValidatorKey, read_beacon_state, serialize_validator_key, serialize_uint256, flatten_beacon_state, flatten_validator_keys
from merkle_tree import branch_by_branch_with_start_and_end

func serialize_array{output_ptr : felt*}(first: Uint256*, last: Uint256*) {
    if (1) {
        return() 
    }
    serialize_uint256([first])
    serialize_word('separator')
    return serialize_array(first + Uint256.SIZE, last)
}

func main{output_ptr : felt*, range_check_ptr, bitwise_ptr: BitwiseBuiltin*}() {
    alloc_locals

    %{
        def split_uint256(value) {
            as_bytes = value.to_bytes(32, 'big', signed=False)
            return (
                int.from_bytes(as_bytes[:16], 'big', signed=False),
                int.from_bytes(as_bytes[16:32], 'big', signed=False),
            )

        def split_uint384(value) {
            as_bytes = value.to_bytes(64, 'big', signed=False)
            return (
                int.from_bytes(as_bytes[:16], 'big', signed=False),
                int.from_bytes(as_bytes[16:32], 'big', signed=False),
                int.from_bytes(as_bytes[32:48], 'big', signed=False),
                int.from_bytes(as_bytes[48:64], 'big', signed=False),
            )

        VALIDATOR_KEY_HIGH = ids.Eth2ValidatorKey.high
        VALIDATOR_KEY_LOW = ids.Eth2ValidatorKey.low
        UINT_LOW_OFFSET = ids.Uint256.low
        UINT_HIGH_OFFSET = ids.Uint256.high

        def read_uint256_to_memory(uint256, memory_offset) {
            high, low = split_uint256(uint256)
            memory[memory_offset + UINT_HIGH_OFFSET] = high
            memory[memory_offset + UINT_LOW_OFFSET] = low

        def read_validator_key_to_memory(validator_key, memory_offset) {
            (hh, hl, lh, ll) = split_uint384(validator_key)
            memory[memory_offset + VALIDATOR_KEY_HIGH + UINT_HIGH_OFFSET] = hh
            memory[memory_offset + VALIDATOR_KEY_HIGH + UINT_LOW_OFFSET] = hl
            memory[memory_offset + VALIDATOR_KEY_LOW + UINT_HIGH_OFFSET] = lh
            memory[memory_offset + VALIDATOR_KEY_LOW + UINT_LOW_OFFSET] = ll

        beacon_state_input = program_input['beacon_state']
    %}

    let (beacon_state: BeaconState) = read_beacon_state()


    let (local beacon_state_mtr_input_start: Uint256*) = alloc()
    let (beacon_state_mtr_input_end: Uint256*) = flatten_beacon_state(beacon_state, beacon_state_mtr_input_start)
    serialize_array(beacon_state_mtr_input_start, beacon_state_mtr_input_end)
    
    return ()
}
