%builtins output range_check bitwise

from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.serialize import serialize_word
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.registers import get_fp_and_pc

from model import BeaconState, ValidatorKeys, Validator, Eth2ValidatorKey, serialize_validator_key, serialize_uint256, read_beacon_state, read_validator_keys, flatten_beacon_state, flatten_validator_keys, assert_key_equal
from merkle_tree import branch_by_branch_with_start_and_end

func serialize_input{output_ptr : felt*}(beacon_state: BeaconState, validator_keys: ValidatorKeys):
    serialize_word('beacon_state')  # 30452092374078856069631800421
    serialize_word(beacon_state.validators_count)
    serialize_validator_key(beacon_state.validators[0].key)
    serialize_word(beacon_state.validators[0].balance)
    serialize_validator_key(beacon_state.validators[1].key)
    serialize_word(beacon_state.validators[1].balance)
    serialize_validator_key(beacon_state.validators[2].key)
    serialize_word(beacon_state.validators[2].balance)
    # serialize_uint256(beacon_state.merkle_tree_root)

    serialize_word('validator_keys')  # 2401043016787086888088334347106675
    serialize_word(validator_keys.keys_count)
    serialize_validator_key(validator_keys.keys[0])
    serialize_validator_key(validator_keys.keys[1])
    # serialize_uint256(validator_keys.merkle_tree_root)
    serialize_word('end')  # 6647396
    return ()
end

func calc_total_locked_value(beacon_state: BeaconState*, validator_keys: ValidatorKeys*) -> (res: felt):
    # General idea here: 
    # * Iterate over all validator_keys
    # * Find the corresponding validator in the beacon state
    # * Sum balances
    #
    # IMPORTANT: using a hint for find_element makes the complexity of finding the validator O(1), and overall complexity O(N).
    #            Without the hint, find_element becomes linear O(M) and overall O(N*M)
    #            Where N - number of Lido validators, M - all validators
    %{
    VALIDATOR_KEY_HIGH = ids.Eth2ValidatorKey.high
    VALIDATOR_KEY_LOW = ids.Eth2ValidatorKey.low
    UINT_LOW_OFFSET = ids.Uint256.low
    UINT_HIGH_OFFSET = ids.Uint256.high

    VALIDATOR_KEY_OFFSET = ids.Validator.key
    VALIDATOR_SIZE = ids.Validator.SIZE

    BEACON_STATE_VALIDATORS_OFFSET = ids.BeaconState.validators

    def validator_key_from_memory(memory_offset):
        addresses =  [
            memory_offset + VALIDATOR_KEY_HIGH + UINT_HIGH_OFFSET,
            memory_offset + VALIDATOR_KEY_HIGH + UINT_LOW_OFFSET,
            memory_offset + VALIDATOR_KEY_LOW + UINT_HIGH_OFFSET,
            memory_offset + VALIDATOR_KEY_LOW + UINT_LOW_OFFSET
        ]
        memory_values = [memory[addr] for addr in addresses]
        key_bytes = b''.join(value.to_bytes(16, byteorder='big') for value in memory_values)
        return int.from_bytes(key_bytes, 'big', signed=False)

    
    validator_lookup = dict()
    validators_mem_addr = ids.beacon_state.validators.address_
    for idx in range(ids.beacon_state.validators_count):
        validator_addr = validators_mem_addr + idx * VALIDATOR_SIZE
        validator_key_addr = validator_addr + VALIDATOR_KEY_OFFSET
        key_from_mem = validator_key_from_memory(validator_key_addr)
        #print(f"KEY[{idx}]: {key_from_mem}")
        validator_lookup[key_from_mem] = idx
    %}

    return calc_total_locked_value_rec(
        validator_key=validator_keys.keys,
        validator_keys_count=validator_keys.keys_count,
        beacon_state=beacon_state,
        curval=0
    )
end

func calc_total_locked_value_rec(validator_key: Eth2ValidatorKey*, validator_keys_count: felt, beacon_state: BeaconState*, curval: felt) -> (res: felt):
    if validator_keys_count == 0:
        return (res=curval)
    end
    let (validator_balance) = find_balance(validator_key, beacon_state)
    return calc_total_locked_value_rec(
        validator_key=validator_key + Eth2ValidatorKey.SIZE,
        validator_keys_count=validator_keys_count - 1,
        beacon_state=beacon_state,
        curval=curval + validator_balance
    )
end

func find_balance(validator_key: Eth2ValidatorKey*, beacon_state: BeaconState*) -> (res: felt):
    # do not call outside calc_total_locked_value - it sets up prover global context (validator_lookup) necessary for this function to execute
    alloc_locals
    local index
    %{
        validator_key_memory_location = ids.validator_key.address_
        validator_key_value = validator_key_from_memory(validator_key_memory_location)
        ids.index = validator_lookup[validator_key_value]
    %}
    let found_validator: Validator = beacon_state.validators[index]
    assert_key_equal([validator_key], found_validator.key) # enforces soundness
    return (res=found_validator.balance)
end

func main{output_ptr : felt*, range_check_ptr, bitwise_ptr: BitwiseBuiltin*}():
    alloc_locals
    # let (__fp__, _) = get_fp_and_pc()  # needed for &new_hash to work

    %{
    beacon_state_input = program_input["beacon_state"]
    validator_keys_input = program_input['validator_keys']
    %}

    let (local beacon_state: BeaconState*) = read_beacon_state()
    let (validator_keys: ValidatorKeys*) = read_validator_keys()

    # Checking the input parsed correctly
    # serialize_input(beacon_state, validator_keys)

    let (local beacon_state_mtr_input_start: Uint256*) = alloc()
    let (beacon_state_mtr_input_end: Uint256*) = flatten_beacon_state([beacon_state], beacon_state_mtr_input_start)
    let (local beacon_state_mtr: Uint256) = branch_by_branch_with_start_and_end(beacon_state_mtr_input_start, beacon_state_mtr_input_end)
    serialize_uint256(beacon_state_mtr)
    # serialize_uint256(beacon_state.merkle_tree_root)

    let (local keys_mtr_input_start: Uint256*) = alloc()
    let (keys_mtr_input_end: Uint256*) = flatten_validator_keys([validator_keys], keys_mtr_input_start)
    let (local validators_mtr: Uint256) = branch_by_branch_with_start_and_end(keys_mtr_input_start, keys_mtr_input_end)
    serialize_uint256(validators_mtr)
    # serialize_uint256(validator_keys.merkle_tree_root)

    let (total_locked_value) = calc_total_locked_value(beacon_state, validator_keys)
    serialize_word(total_locked_value)

    
    return ()
end
