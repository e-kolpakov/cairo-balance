from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bitwise import bitwise_and
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.default_dict import (
    default_dict_new,
    default_dict_finalize,
)
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.dict import dict_read, dict_write, dict_update, dict_squash
from starkware.cairo.common.registers import get_fp_and_pc

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

func create_initial_branches{range_check_ptr}(zerohashes: Uint256*, size: felt) -> (branches_start: DictAccess*, branches_end: DictAccess*, default_val: felt):
    alloc_locals
    let first_zerohash = cast(&zerohashes[0], felt)
    let (local initial_branches) = default_dict_new(default_value=first_zerohash)
    let (local branch_end) = create_initial_branches_rec(
        zerohash=zerohashes,
        acc=initial_branches,
        index=0,
        max_index=size
    )
    return (branches_start=initial_branches, branches_end=branch_end, default_val=first_zerohash)
end

func create_initial_branches_rec{range_check_ptr}(zerohash: Uint256*, acc: DictAccess*, index: felt, max_index: felt) -> (res: DictAccess*):
    if index == max_index:
        return (res=acc)
    end
    let zerohash_felt_addr = cast(zerohash, felt)
    dict_write{dict_ptr=acc}(key=index, new_value=zerohash_felt_addr)
    return create_initial_branches_rec(
        zerohash=zerohash + Uint256.SIZE,
        acc=acc,
        index=index+1,
        max_index=max_index
    )
end

func add_values{branches: DictAccess*, bitwise_ptr: BitwiseBuiltin*, range_check_ptr}(value: Uint256*, index: felt, max_index: felt):
    if index == max_index:
        return()
    end
    add_value{branches=branches}([value], index)
    return add_values{branches=branches}(value=value+Uint256.SIZE, index=index+1, max_index=max_index)
end

func add_value{branches: DictAccess*, bitwise_ptr: BitwiseBuiltin*, range_check_ptr}(value: Uint256, index: felt):
    alloc_locals
    let (local new_hash, height) = _add_value_rec(index + 1, value, 0, 1)
    let (__fp__, _) = get_fp_and_pc()  # needed for &new_hash to work
    let casted = cast(&new_hash, felt)
    dict_write{dict_ptr=branches}(key=height, new_value=casted)
    return()
end

func _add_value_rec{branches: DictAccess*, range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(index: felt, cur_hash: Uint256, height: felt, mask: felt) -> (hash: Uint256, height: felt): 
    # alloc_locals is  needed for automatic implicit reference rebinding
    # see https://www.cairo-lang.org/docs/how_cairo_works/builtins.html#revoked-implicit-arguments
    alloc_locals
    let (exit_condition_check) = bitwise_and(index, mask)
    if exit_condition_check != 0:
        return (cur_hash, height)
    end
    let (branch) = _get_hash_from_branch{branches=branches}(height)
    let (new_hash) = keccak2(branch, cur_hash)
    return _add_value_rec{branches=branches}(
        index=index,
        cur_hash=new_hash,
        height=height+1,
        mask=mask*2 + 1
    )
end

func _get_hash_from_branch{branches: DictAccess*}(height: felt) -> (res: Uint256):
    alloc_locals
    let (local branch_ref: felt)  = dict_read{dict_ptr=branches}(key=height)
    let casted_branch_ref: Uint256* = cast(branch_ref, Uint256*)
    let branch = [casted_branch_ref]
    return (res=branch)
end

func get_root_from_branches{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, branches: DictAccess*}(zerohashes: Uint256*, size: felt, max_height: felt) -> (res: Uint256):
    %{
        def read_uint256_to_hex_str(value):
            high, low = value.get_or_set_value('high', None), value.get_or_set_value('low', None)
            as_bytes = high.to_bytes(16, 'big', signed=False) + low.to_bytes(16, 'big', signed=False)
            as_int = int.from_bytes(as_bytes, 'big', signed=False)
            return f'{as_int:#x}'
    %}
    let cur_hash = zerohashes[0]
    return _get_root_from_branches_rec{branches=branches}(
        zerohashes=zerohashes,
        size=size,
        cur_hash=cur_hash,
        height=0,
        max_height=max_height,
        mask=1
    )
end

func _get_root_from_branches_rec{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, branches: DictAccess*}(zerohashes: Uint256*, size: felt, cur_hash: Uint256, height: felt, max_height: felt, mask:felt) -> (res: Uint256):
    # alloc_locals is  needed for automatic implicit reference rebinding
    # see https://www.cairo-lang.org/docs/how_cairo_works/builtins.html#revoked-implicit-arguments
    alloc_locals
    if height == max_height:
        return (res=cur_hash)
    end
    let (use_branch_check) = bitwise_and(size, mask)
    if use_branch_check == mask:
        let (branch) = _get_hash_from_branch{branches=branches}(height)
        %{ 
            # side = f"h{ids.height}-branch" 
        %}
        let (local new_hash_res) = keccak2(branch, cur_hash)
        tempvar new_hash = new_hash_res
        tempvar branches = branches
    else:
        %{ 
        #    side = f"h{ids.height}-zerohash" 
        %}
        let (local new_hash_res) = keccak2(cur_hash, zerohashes[height])
        tempvar new_hash = new_hash_res
        tempvar branches = branches
    end
    %{ 
        #print(f"{side}, {read_uint256_to_hex_str(ids.new_hash)}") 
    %}
    return _get_root_from_branches_rec{branches=branches}(
        zerohashes=zerohashes,
        size=size,
        cur_hash=new_hash,
        height=height+1,
        max_height=max_height,
        mask=mask*2
    )
end

func branch_by_branch{range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(values: Uint256*, size: felt) -> (res: Uint256):
    alloc_locals
    const TREE_HEIGHT = 32
    let (local zerohashes: Uint256*, max_height) = calc_zerohashes(TREE_HEIGHT)
    let (local branches_start: DictAccess*, branches_end: DictAccess*, default_val: felt) = create_initial_branches(zerohashes, max_height)
    
    add_values{branches=branches_end}(values, index=0, max_index=size)

    let (local merkle_tree_root: Uint256) = get_root_from_branches{branches=branches_end}(
        zerohashes=zerohashes,
        size=size,
        max_height=TREE_HEIGHT
    )

    # squashing to vefiry entire set of operations on branches is sound
    let (branches_start, branches_end) = dict_squash(branches_start, branches_end)
    return (res=merkle_tree_root)
end