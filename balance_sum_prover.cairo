%builtins output range_check bitwise

from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.serialize import serialize_word
from starkware.cairo.common.alloc import alloc

from model import BeaconState, ValidatorKeys, Validator, Eth2ValidatorKey, serialize_validator_key, serialize_uint256, flatten_beacon_state, flatten_validator_keys


# tail-recursive sum
# func verify_and_calc_account_balance_sum{range_check_ptr}(accounts: Account*, size: felt, acc: felt) -> (res: felt):
#     if size == 0:
#         return (res=acc)
#     end
#     let balance = accounts[0].balance
#     assert [range_check_ptr] = balance # verifies that 0 <= balance <= 2**128
#     let range_check_ptr = range_check_ptr + 1
#     return verify_and_calc_account_balance_sum(
#         accounts = accounts + Account.SIZE,
#         size = size - 1,
#         acc = acc + balance
#     )
# end

func read_beacon_state() -> (res: BeaconState):
    alloc_locals
    local beacon_state: BeaconState
    %{
        BEACON_STATE_VALIDATOR_COUNT = ids.BeaconState.validators_count
        BEACON_STATE_MTR = ids.BeaconState.merkle_tree_root
        BEACON_STATE_VALIDATORS = ids.BeaconState.validators

        VALIDATOR_BALANCE = ids.Validator.balance
        VALIDATOR_KEY = ids.Validator.key
        VALIDATOR_SIZE = ids.Validator.SIZE

        KEY_HIGH = ids.Eth2ValidatorKey.high
        KEY_LOW = ids.Eth2ValidatorKey.high


        beacon_state = program_input['beacon_state']
        validators = beacon_state['validators']
        beacon_state_mtr = int(program_input['beacon_state_mtr'], 16)

        beacon_state_addr = ids.beacon_state.address_
        beacon_state_validators = segments.add()
        memory[beacon_state_addr + BEACON_STATE_VALIDATOR_COUNT] = len(validators)
        memory[beacon_state_addr + BEACON_STATE_VALIDATORS] = beacon_state_validators
        read_uint256_to_memory(beacon_state_mtr, beacon_state_addr + BEACON_STATE_MTR)

        for (idx, validator) in enumerate(validators):
            current_addr = beacon_state_validators + idx * VALIDATOR_SIZE
            read_validator_key_to_memory(int(validator["pubkey"], 16), current_addr + VALIDATOR_KEY)
            read_uint256_to_memory(int(validator["balance"]), current_addr + VALIDATOR_BALANCE)

    %}
    return (res=beacon_state)
end

func read_validator_keys() -> (res: ValidatorKeys):
    alloc_locals
    local validator_keys: ValidatorKeys

    %{
        VALIDATOR_KEYS_COUNT = ids.ValidatorKeys.keys_count
        VALIDATOR_KEYS_KEYS = ids.ValidatorKeys.keys
        VALIDATOR_KEYS_MTR = ids.ValidatorKeys.merkle_tree_root
        KEY_SIZE = ids.Eth2ValidatorKey.SIZE

        validator_keys = program_input['validator_keys']
        validator_keys_mtr = int(program_input['validator_keys_mtr'], 16)
        validator_keys_addr = ids.validator_keys.address_
        keys = segments.add()
        memory[validator_keys_addr + VALIDATOR_KEYS_COUNT] = len(validator_keys)
        memory[validator_keys_addr + VALIDATOR_KEYS_KEYS] = keys
        read_uint256_to_memory(validator_keys_mtr, validator_keys_addr + VALIDATOR_KEYS_MTR)

        for (idx, key) in enumerate(validator_keys):
            current_addr = keys + idx * KEY_SIZE
            read_validator_key_to_memory(int(key, 16), current_addr)
    %}
    return (res=validator_keys)
end


func serialize_input{output_ptr : felt*}(beacon_state: BeaconState, validator_keys: ValidatorKeys):
    serialize_word('beacon_state')  # 30452092374078856069631800421
    serialize_word(beacon_state.validators_count)
    serialize_validator_key(beacon_state.validators[0].key)
    serialize_uint256(beacon_state.validators[0].balance)
    serialize_validator_key(beacon_state.validators[1].key)
    serialize_uint256(beacon_state.validators[1].balance)
    serialize_validator_key(beacon_state.validators[2].key)
    serialize_uint256(beacon_state.validators[2].balance)
    serialize_uint256(beacon_state.merkle_tree_root)

    serialize_word('validator_keys')  # 2401043016787086888088334347106675
    serialize_word(validator_keys.keys_count)
    serialize_validator_key(validator_keys.keys[0])
    serialize_validator_key(validator_keys.keys[1])
    serialize_uint256(validator_keys.merkle_tree_root)
    serialize_word('end')  # 6647396
    return ()
end

func main{output_ptr : felt*, range_check_ptr, bitwise_ptr: BitwiseBuiltin*}():
    alloc_locals

    %{
        def split_uint256(value):
            as_bytes = value.to_bytes(32, 'big', signed=False)
            return (
                int.from_bytes(as_bytes[:16], 'big', signed=False),
                int.from_bytes(as_bytes[16:32], 'big', signed=False),
            )

        def split_uint384(value):
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

        def read_validator_key_to_memory(validator_key, memory_offset):
            (hh, hl, lh, ll) = split_uint384(validator_key)
            memory[memory_offset + VALIDATOR_KEY_HIGH + UINT_HIGH_OFFSET] = hh
            memory[memory_offset + VALIDATOR_KEY_HIGH + UINT_LOW_OFFSET] = hl
            memory[memory_offset + VALIDATOR_KEY_LOW + UINT_HIGH_OFFSET] = lh
            memory[memory_offset + VALIDATOR_KEY_LOW + UINT_LOW_OFFSET] = ll

        def read_uint256_to_memory(uint256, memory_offset):
            high, low = split_uint256(uint256)
            memory[memory_offset + UINT_HIGH_OFFSET] = high
            memory[memory_offset + UINT_LOW_OFFSET] = low
    %}  

    let (beacon_state: BeaconState) = read_beacon_state()
    let (validator_keys: ValidatorKeys) = read_validator_keys()

    # Checking the input parsed correctly
    # serialize_input(beacon_state, validator_keys)

    let (local beacon_state_mtr_input_start: Uint256*) = alloc()
    let (beacon_state_mtr_input_end: Uint256*) = flatten_beacon_state(beacon_state, beacon_state_mtr_input_start)

    # serialize_uint256(beacon_state_mtr_input_start[0])
    # serialize_uint256(beacon_state_mtr_input_start[1])
    # serialize_uint256(beacon_state_mtr_input_start[2])
    # serialize_uint256(beacon_state_mtr_input_start[3])
    # serialize_uint256(beacon_state_mtr_input_start[4])
    # serialize_uint256(beacon_state_mtr_input_start[5])
    # serialize_uint256(beacon_state_mtr_input_start[6])
    # serialize_uint256(beacon_state_mtr_input_start[7])
    # serialize_uint256(beacon_state_mtr_input_start[8])

    let (local keys_mtr_input_start: Uint256*) = alloc()
    let (keys_mtr_input_end: Uint256*) = flatten_validator_keys(validator_keys, keys_mtr_input_start)
    serialize_uint256(keys_mtr_input_start[0])
    serialize_uint256(keys_mtr_input_start[1])
    serialize_uint256(keys_mtr_input_start[2])
    serialize_uint256(keys_mtr_input_start[3])
    # let (merkle_tree_root) = calc_account_merkle_tree(accounts, 0, size)
    # assert merkle_tree_root.high = keccak_merkle_tree_root.high
    # assert merkle_tree_root.low = keccak_merkle_tree_root.low
    # serialize_word(merkle_tree_root.high)
    # serialize_word(merkle_tree_root.low)

    # let (account_balance_sum) = verify_and_calc_account_balance_sum(accounts, size, 0)
    # serialize_word(account_balance_sum)
    return ()
end
