from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.serialize import serialize_word

# Validator keys are 96 hex => 48 bytes => 2**384 - higher than what fits into felt
struct Eth2ValidatorKey:
    member high: Uint256
    member low: Uint256
end

struct Validator:
    member key: Eth2ValidatorKey
    member balance: Uint256
end

struct BeaconState:
    member validators_count: felt
    member validators: Validator*
    member merkle_tree_root: Uint256
end

struct ValidatorKeys:
    member keys_count: felt
    member keys: Eth2ValidatorKey*
    member merkle_tree_root: Uint256
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

func flatten_beacon_state(beacon_state: BeaconState, target: Uint256*) -> (res: Uint256*):
    return flatten_validators(
        validator = beacon_state.validators,
        count = beacon_state.validators_count,
        target=target
    )
end

func flatten_validators(validator: Validator*, count: felt, target: Uint256*) -> (res: Uint256*):
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

func flatten_validator(validator: Validator*, target: Uint256*) -> (res: Uint256*):
    assert target[0] = validator.key.high
    assert target[1] = validator.key.low
    assert target[2] = validator.balance
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