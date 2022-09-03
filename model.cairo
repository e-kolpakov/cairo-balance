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
    serialize_word(value.high)
    serialize_word(value.low)
    return()
end
