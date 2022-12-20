from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.serialize import serialize_word
from starkware.cairo.common.math import split_felt
from starkware.cairo.common.registers import get_fp_and_pc

# Validator keys are 96 hex => 48 bytes => 2**384 - higher than what fits into felt
struct Eth2ValidatorKey:
    member high: Uint256
    member low: Uint256
end

struct Validator:
    member key: Eth2ValidatorKey
    member balance: felt
end

struct BeaconState:
    member validators_count: felt
    member validators: Validator*
    # member merkle_tree_root: Uint256
end

struct ValidatorKeys:
    member keys_count: felt
    member keys: Eth2ValidatorKey*
    # member merkle_tree_root: Uint256
end


func serialize_validator_key{output_ptr : felt*}(value: Eth2ValidatorKey):
    serialize_word(value.high.high)
    serialize_word(value.high.low)
    serialize_word(value.low.high)
    serialize_word(value.low.low)
    return ()
end

func serialize_uint256{output_ptr : felt*}(value: Uint256):
    # output is big-endian
    serialize_word(value.high)
    serialize_word(value.low)
    return()
end

func assert_key_equal(left: Eth2ValidatorKey, right: Eth2ValidatorKey):
    assert left.high.high = right.high.high
    assert left.high.low = right.high.low
    assert left.low.high = right.low.high
    assert left.low.low = right.low.low
    return()
end

func flatten_beacon_state{range_check_ptr}(beacon_state: BeaconState, target: Uint256*) -> (res: Uint256*):
    return flatten_validators(
        validator = beacon_state.validators,
        count = beacon_state.validators_count,
        target=target
    )
end

func flatten_validators{range_check_ptr}(validator: Validator*, count: felt, target: Uint256*) -> (res: Uint256*):
    if count == 0:
        return (res=target)
    end
    let (new_target: Uint256*) = flatten_validator(validator, target)
    let next_validator: Validator* = validator + Validator.SIZE
    return flatten_validators(
        validator=next_validator,
        count = count - 1,
        target = new_target,
    )
end

func flatten_validator{range_check_ptr}(validator: Validator*, target: Uint256*) -> (res: Uint256*):
    assert target[0] = validator.key.high
    assert target[1] = validator.key.low
    let (high, low) = split_felt(validator.balance)
    assert target[2] = Uint256(low=low, high=high)
    return (res=target + 3 * Uint256.SIZE)
end

func flatten_validator_keys(validator_keys: ValidatorKeys, target: Uint256*) -> (res: Uint256*):
    return flatten_validator_keys_inner(
        key = validator_keys.keys,
        count = validator_keys.keys_count,
        target=target
    )
end

func flatten_validator_keys_inner(key: Eth2ValidatorKey*, count: felt, target: Uint256*) -> (res: Uint256*):
    if count == 0:
        return (res=target)
    end
    let next_key = key + Eth2ValidatorKey.SIZE

    assert target[0] = key.high
    assert target[1] = key.low
    return flatten_validator_keys_inner(
        key=next_key,
        count = count - 1,
        target = target + 2 * Uint256.SIZE
    )
end

func init_hints():
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
    return()
end

func read_beacon_state() -> (res: BeaconState*):
    alloc_locals
    local beacon_state: BeaconState
    init_hints()
    %{
        # Expects dependencies:
        # * read_uint256_to_memory
        # * beacon_state_input
        # * read_validator_key_to_memory
        beacon_state = beacon_state_input
        validators = beacon_state['validators']
        # beacon_state_mtr = int(program_input['beacon_state_mtr'], 16)

        validators_lookup = dict()

        BEACON_STATE_VALIDATOR_COUNT = ids.BeaconState.validators_count
        BEACON_STATE_VALIDATORS = ids.BeaconState.validators
        #BEACON_STATE_MTR = ids.BeaconState.merkle_tree_root

        VALIDATOR_BALANCE = ids.Validator.balance
        VALIDATOR_KEY = ids.Validator.key
        VALIDATOR_SIZE = ids.Validator.SIZE

        KEY_HIGH = ids.Eth2ValidatorKey.high
        KEY_LOW = ids.Eth2ValidatorKey.high

        beacon_state_addr = ids.beacon_state.address_
        beacon_state_validators = segments.add()
        memory[beacon_state_addr + BEACON_STATE_VALIDATOR_COUNT] = len(validators)
        memory[beacon_state_addr + BEACON_STATE_VALIDATORS] = beacon_state_validators
        #read_uint256_to_memory(beacon_state_mtr, beacon_state_addr + BEACON_STATE_MTR)

        for (idx, validator) in enumerate(validators):
            current_addr = beacon_state_validators + idx * VALIDATOR_SIZE
            key, balance = int(validator["pubkey"], 16), int(validator["balance"])
            validators_lookup[key] = balance
            read_validator_key_to_memory(key, current_addr + VALIDATOR_KEY)
            # read_uint256_to_memory(balance, current_addr + VALIDATOR_BALANCE)
            memory[current_addr + VALIDATOR_BALANCE] = balance

    %}
    let (__fp__, _) = get_fp_and_pc()  # needed for &new_hash to work
    return (res=&beacon_state)
end

func read_validator_keys() -> (res: ValidatorKeys*):
    alloc_locals
    local validator_keys: ValidatorKeys
    init_hints()
    %{
        # Expects dependencies:
        # * validator_keys_input
        # * read_validator_key_to_memory
        VALIDATOR_KEYS_COUNT = ids.ValidatorKeys.keys_count
        VALIDATOR_KEYS_KEYS = ids.ValidatorKeys.keys
        # VALIDATOR_KEYS_MTR = ids.ValidatorKeys.merkle_tree_root
        KEY_SIZE = ids.Eth2ValidatorKey.SIZE
        
        # validator_keys_mtr = int(program_input['validator_keys_mtr'], 16)
        validator_keys_addr = ids.validator_keys.address_
        keys = segments.add()
        memory[validator_keys_addr + VALIDATOR_KEYS_COUNT] = len(validator_keys_input)
        memory[validator_keys_addr + VALIDATOR_KEYS_KEYS] = keys
        #read_uint256_to_memory(validator_keys_mtr, validator_keys_addr + VALIDATOR_KEYS_MTR)

        for (idx, key) in enumerate(validator_keys_input):
            current_addr = keys + idx * KEY_SIZE
            read_validator_key_to_memory(int(key, 16), current_addr)
    %}
    let (__fp__, _) = get_fp_and_pc()  # needed for &new_hash to work
    return (res=&validator_keys)
end