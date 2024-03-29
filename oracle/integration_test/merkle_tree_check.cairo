%builtins output range_check bitwise

from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.serialize import serialize_word
from merkle_tree import calc_zerohashes, branch_by_branch, branch_by_branch_with_start_and_end

from model import serialize_uint256

func serialize_uint256_array{output_ptr : felt*}(current_element: Uint256*, size: felt) {
    if (size == 0) {
        return ();
    }
    serialize_uint256([current_element]);
    return serialize_uint256_array(current_element + Uint256.SIZE, size-1);
}

func read_input() -> (res: Uint256*, size: felt) {
    alloc_locals;
    local input_size: felt;
    local values: Uint256*;

    %{
        UINT_LOW_OFFSET = ids.Uint256.low
        UINT_HIGH_OFFSET = ids.Uint256.high

        data = program_input['data']
        ids.input_size = len(data)
        values_mem_offset = ids.values = segments.add()
        for (idx, record) in enumerate(data):
            memory_offset = values_mem_offset + idx * ids.Uint256.SIZE
            high, low = split_uint256(record)
            memory[memory_offset + UINT_HIGH_OFFSET] = high
            memory[memory_offset + UINT_LOW_OFFSET] = low

    %}
    return (res=values, size=input_size);
}


func main{output_ptr : felt*, range_check_ptr, bitwise_ptr: BitwiseBuiltin*}() {
    alloc_locals;
    %{
        def split_uint256(value):
            as_bytes = value.to_bytes(32, 'big', signed=False)
            return (
                int.from_bytes(as_bytes[:16], 'big', signed=False),
                int.from_bytes(as_bytes[16:32], 'big', signed=False),
            )

        def read_uint256_to_memory(uint256, memory_offset):
            high, low = split_uint256(uint256)
            memory[memory_offset + UINT_HIGH_OFFSET] = high
            memory[memory_offset + UINT_LOW_OFFSET] = low
    %}

    let (local values, input_size) = read_input();
    //  let (local zerohashes: Uint256*, _) = calc_zerohashes(TREE_DEPTH)
    //  let (local merkle_tree_root: Uint256) = branch_by_branch(values, input_size)
    let values_end = values + input_size * Uint256.SIZE;
    let (local merkle_tree_root: Uint256) = branch_by_branch_with_start_and_end(values, values_end);
    serialize_uint256(merkle_tree_root);
    return ();
}