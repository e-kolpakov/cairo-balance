from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.keccak import keccak_felts, unsafe_keccak_init, unsafe_keccak_finalize, KeccakState, unsafe_keccak_add_uint256
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.registers import get_fp_and_pc

from account import Account

func keccak2{range_check_ptr}(left: Uint256, right: Uint256) -> (res: Uint256):
    let (keccak_state) = unsafe_keccak_init()
    unsafe_keccak_add_uint256{keccak_state=keccak_state}(left)
    unsafe_keccak_add_uint256{keccak_state=keccak_state}(right)
    let (res) = unsafe_keccak_finalize(keccak_state=keccak_state)
    return (res=res)
end

func account_keccak{range_check_ptr}(account: Account) -> (res: Uint256):
    # Original pre-optimization code
    alloc_locals
    let (ptr) = alloc()
    assert [ptr] = account.address
    assert [ptr+1] = account.balance

    return keccak_felts(2, ptr)

    # Optimized version - saving on allocations and cairo.common.math.split_felt
    # make sure the address and balance are in [0; 2**128) range]
    # These checks are actually redundant - eth address is 40 hex => 2**80 at most; balance is even smaller
    # assert [range_check_ptr] = account.address
    # assert [range_check_ptr+1] = account.balance
    # let range_check_ptr = range_check+2
    
    # let (__fp__, _) = get_fp_and_pc()
    # let account_address = &account

    # let keccak_state: KeccakState = KeccakState(start_ptr=account_address, end_ptr=account_address+Account.SIZE)
    # let (res) = unsafe_keccak_finalize(keccak_state=keccak_state)
    # return (res=res)
end