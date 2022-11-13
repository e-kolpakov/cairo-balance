from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.common.keccak import keccak_felts, unsafe_keccak_init, unsafe_keccak_finalize, KeccakState, unsafe_keccak_add_uint256
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.registers import get_fp_and_pc


func keccak2{range_check_ptr}(left: Uint256, right: Uint256) -> (res: Uint256):
    let (keccak_state) = unsafe_keccak_init()
    unsafe_keccak_add_uint256{keccak_state=keccak_state}(left)
    unsafe_keccak_add_uint256{keccak_state=keccak_state}(right)
    let (res) = unsafe_keccak_finalize(keccak_state=keccak_state)
    return (res=res)
end
