%builtins output range_check

from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.keccak import keccak_felts
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.serialize import serialize_word
from keccak_utils import account_keccak


func main{output_ptr : felt*, range_check_ptr}():
    alloc_locals
    local account: Account
    local keccak_merkle_tree_root: Uint256

    %{
        account = program_input['account']

        ADDRESS_OFFSET = ids.Account.address
        BALANCE_OFFSET = ids.Account.balance

        addr = ids.account.address_
        memory[addr + ADDRESS_OFFSET] = account["address"]
        memory[addr + BALANCE_OFFSET] = account["balance"]

        LOW_OFFSET = ids.Uint256.low
        HIGH_OFFSET = ids.Uint256.high

        addr = ids.keccak_merkle_tree_root.address_
        memory[addr + LOW_OFFSET] = program_input['account_hash']['low']
        memory[addr + HIGH_OFFSET] = program_input['account_hash']['high']
    %}
    serialize_word(account.address)
    serialize_word(account.balance)

    let (account_hash) = account_keccak(account)
    serialize_word(account_hash.low)
    serialize_word(account_hash.high)
    assert account_hash.high = keccak_merkle_tree_root.high
    assert account_hash.low = keccak_merkle_tree_root.low
    return ()
end