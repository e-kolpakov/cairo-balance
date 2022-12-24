%builtins output range_check

from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.serialize import serialize_word
from merkle_tree import calc_zerohashes

from model import serialize_uint256

func serialize_uint256_array{output_ptr : felt*}(current_element: Uint256*, size: felt) {
    if (size == 0) {
        return ();
    }
    serialize_uint256([current_element]);
    return serialize_uint256_array(current_element + Uint256.SIZE, size-1);
}


func main{output_ptr : felt*, range_check_ptr}() {
    alloc_locals;
    const TREE_DEPTH = 32;
    let (local zerohashes: Uint256*, _) = calc_zerohashes(TREE_DEPTH);
    serialize_uint256_array(zerohashes, TREE_DEPTH);
    return ();
}