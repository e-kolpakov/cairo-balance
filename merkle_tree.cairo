from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.bitwise import bitwise_and

from keccak_utils import account_keccak, keccak2
from account import Account

func div_2{bitwise_ptr: BitwiseBuiltin*}(value:felt) -> (res:felt):
    let (result) = bitwise_and(value, 1)
    if result != 0:
        return ((value - 1) / 2)
    else:
        return (value / 2)
    end
end

func calc_account_merkle_tree{range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(balances: Account*, left_boundary, right_boundary) -> (res: Uint256):
    alloc_locals
    let size = right_boundary - left_boundary
    if size == 1:
        let (result) = account_keccak(balances[left_boundary])
        return (result)
    end

    let (half) = div_2(size)
    local center = left_boundary + half
    let (left) = calc_account_merkle_tree(balances, left_boundary, center)
    let (right) = calc_account_merkle_tree(balances, center, right_boundary)
    let (result) = keccak2(left, right)
    return (result)
end