%builtins output range_check bitwise

from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.serialize import serialize_word
from starkware.cairo.common.alloc import alloc

from model import BeaconState, ValidatorKeys, Validator, Eth2ValidatorKey, serialize_validator_key, serialize_uint256, read_beacon_state, read_validator_keys, flatten_beacon_state, flatten_validator_keys
from merkle_tree import branch_by_branch_with_start_and_end

func serialize_input{output_ptr : felt*}(beacon_state: BeaconState, validator_keys: ValidatorKeys):
    serialize_word('beacon_state')  # 30452092374078856069631800421
    serialize_word(beacon_state.validators_count)
    serialize_validator_key(beacon_state.validators[0].key)
    serialize_uint256(beacon_state.validators[0].balance)
    serialize_validator_key(beacon_state.validators[1].key)
    serialize_uint256(beacon_state.validators[1].balance)
    serialize_validator_key(beacon_state.validators[2].key)
    serialize_uint256(beacon_state.validators[2].balance)
    # serialize_uint256(beacon_state.merkle_tree_root)

    serialize_word('validator_keys')  # 2401043016787086888088334347106675
    serialize_word(validator_keys.keys_count)
    serialize_validator_key(validator_keys.keys[0])
    serialize_validator_key(validator_keys.keys[1])
    # serialize_uint256(validator_keys.merkle_tree_root)
    serialize_word('end')  # 6647396
    return ()
end

func calc_total_locked_value(beacon_state: BeaconState, validator_keys: ValidatorKeys) -> (res: Uint256):
    return(res=Uint256(low=0, high=0))
end

func main{output_ptr : felt*, range_check_ptr, bitwise_ptr: BitwiseBuiltin*}():
    alloc_locals

    %{
    beacon_state_input = program_input["beacon_state"]
    validator_keys = program_input['validator_keys']
    %}

    let (beacon_state: BeaconState) = read_beacon_state()
    let (validator_keys: ValidatorKeys) = read_validator_keys()

    # Checking the input parsed correctly
    # serialize_input(beacon_state, validator_keys)

    let (local beacon_state_mtr_input_start: Uint256*) = alloc()
    let (beacon_state_mtr_input_end: Uint256*) = flatten_beacon_state(beacon_state, beacon_state_mtr_input_start)
    let (local beacon_state_mtr: Uint256) = branch_by_branch_with_start_and_end(beacon_state_mtr_input_start, beacon_state_mtr_input_end)
    serialize_uint256(beacon_state_mtr)
    # serialize_uint256(beacon_state.merkle_tree_root)

    let (local keys_mtr_input_start: Uint256*) = alloc()
    let (keys_mtr_input_end: Uint256*) = flatten_validator_keys(validator_keys, keys_mtr_input_start)
    let (local validators_mtr: Uint256) = branch_by_branch_with_start_and_end(keys_mtr_input_start, keys_mtr_input_end)
    serialize_uint256(validators_mtr)
    # serialize_uint256(validator_keys.merkle_tree_root)


    let (total_locked_value) = calc_total_locked_value(beacon_state, validator_keys)
    serialize_uint256(total_locked_value)

    
    return ()
end
