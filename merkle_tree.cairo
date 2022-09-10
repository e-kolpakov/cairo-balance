from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bitwise import bitwise_and
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.uint256 import Uint256

from keccak_utils import keccak2

func div_2{bitwise_ptr: BitwiseBuiltin*}(value:felt) -> (res:felt):
    let (result) = bitwise_and(value, 1)
    if result != 0:
        return ((value - 1) / 2)
    else:
        return (value / 2)
    end
end

# Replica of https://github.com/ethereum/research/blob/master/beacon_chain_impl/progressive_merkle_tree.py

func calc_zerohashes{range_check_ptr}(depth: felt) -> (res: Uint256*, size: felt):
    alloc_locals
    let (local result: Uint256*) = alloc()
    assert result[0] = Uint256(low=0, high=0)
    let (res) = _calc_zerohashes_rec(result, 0, depth)
    return (res=res, size=depth) 
end

func _calc_zerohashes_rec{range_check_ptr}(result: Uint256*, current_idx: felt, max_depth: felt) -> (res: Uint256*):
    if current_idx == max_depth - 1:
        return (result)
    end
    let current_elem = result[current_idx]
    let next_idx = current_idx+1
    let (next_hash) = keccak2(current_elem, current_elem)
    assert result[next_idx] = next_hash
    return _calc_zerohashes_rec(
        result = result,
        current_idx = next_idx,
        max_depth = max_depth
    )
end