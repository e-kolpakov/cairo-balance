%builtins output range_check bitwise

from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.bitwise import bitwise_and
from starkware.cairo.common.serialize import serialize_word

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

func calc_account_merkle_tree{output_ptr: felt*, range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(balances: Account*, left_boundary, right_boundary) -> (res: Uint256):
    alloc_locals
    let size = right_boundary - left_boundary
    if size == 1:
        let addr = balances + left_boundary * Account.SIZE
        let (result) = account_keccak([addr])
        return (result)
    end

    let (half) = div_2(size)
    local center = left_boundary + half
    let (left) = calc_account_merkle_tree(balances, left_boundary, center)
    let (right) = calc_account_merkle_tree(balances, center, right_boundary)
    let (result) = keccak2(left, right)
    # serialize_word(1000000)
    # serialize_word(result.high)
    # serialize_word(result.low)
    return (result)
end

# tail-recursive sum
func verify_and_calc_account_balance_sum{range_check_ptr}(accounts: Account*, size: felt, acc: felt) -> (res: felt):
    if size == 0:
        return (res=acc)
    end
    let address = accounts[0].address
    let balance = accounts[0].balance
    assert [range_check_ptr] = address # verifies that 0 <= balance <= 2**128
    assert [range_check_ptr+1] = balance # verifies that 0 <= balance <= 2**128
    let range_check_ptr = range_check_ptr + 2
    return verify_and_calc_account_balance_sum(
        accounts = accounts + Account.SIZE,
        size = size - 1,
        acc = acc + balance
    )
end

func main{output_ptr : felt*, range_check_ptr, bitwise_ptr: BitwiseBuiltin*}():
    alloc_locals
    local accounts: Account*
    local size: felt
    local keccak_merkle_tree_root: Uint256

    %{
        accounts_input = program_input['accounts']

        ADDRESS_OFFSET = ids.Account.address
        BALANCE_OFFSET = ids.Account.balance

        ids.accounts = accounts = segments.add()
        for idx, account in enumerate(accounts_input):
            memory[accounts + (2*idx) + ADDRESS_OFFSET] = account["address"]
            memory[accounts + (2*idx) + BALANCE_OFFSET] = account["balance"]

        ids.size = len(accounts_input)

        LOW_OFFSET = ids.Uint256.low
        HIGH_OFFSET = ids.Uint256.high

        addr = ids.keccak_merkle_tree_root.address_
        memory[addr + LOW_OFFSET] = program_input['merkle_tree_root']['low']
        memory[addr + HIGH_OFFSET] = program_input['merkle_tree_root']['high']
    %}

    let (merkle_tree_root) = calc_account_merkle_tree(accounts, 0, size)
    assert merkle_tree_root.high = keccak_merkle_tree_root.high
    assert merkle_tree_root.low = keccak_merkle_tree_root.low
    serialize_word(merkle_tree_root.high)
    serialize_word(merkle_tree_root.low)

    let (account_balance_sum) = verify_and_calc_account_balance_sum(accounts, size, 0)
    serialize_word(account_balance_sum)
    return ()
end
