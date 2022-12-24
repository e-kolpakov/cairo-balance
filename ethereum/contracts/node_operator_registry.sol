pragma solidity ^0.8.6;

// import "GNSPS/solidity-bytes-utils@0.8.0/contracts/BytesLib.sol";
import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/utils/math/SafeMath.sol";
import "@ganache/console.log/console.sol";

contract NodeOperatorRegistry {
    using SafeMath for uint256;

    event MTRLeafAdded(
        uint index,
        bytes32 value
    );

    uint256 constant public PUBKEY_LENGTH = 48;
    uint256 key_count;

    uint constant TREE_DEPTH = 32;
    uint constant MAX_KEYS_COUNT = 2**TREE_DEPTH - 1;
    bytes32[TREE_DEPTH] zero_hashes;
    bytes32[TREE_DEPTH] branch;

    address public contractAdmin;

    modifier onlyContractAdmin() {
        require(msg.sender == contractAdmin, "AUTH_FAILED");
        _;
    }

    constructor(address _contractAdmin) {
        contractAdmin = _contractAdmin;

        for (uint height = 0; height < TREE_DEPTH - 1; height++)
            zero_hashes[height + 1] = keccak256(abi.encodePacked(zero_hashes[height], zero_hashes[height]));
    }

    /// @notice Add validator key.
    function add_key(bytes calldata pubkey) external {
        require(pubkey.length == 48, "NodeOperatorContract: invalid pubkey length");
        require(key_count < PUBKEY_LENGTH, "NodeOperatorContract: merkle tree full");

        // See "Merkle tree leaves content" section in readme for details
        bytes32[2] memory key_parts = [
            // This preserves the endianness - pubkey is 48bytes big-endian, so
            // to pad to a 64 byte preserving endianness we have to add zeroes in front
            bytes32(abi.encodePacked(bytes16(0), pubkey[:16])),
            bytes32(pubkey[16:48])
        ];
        uint old_key_count = key_count;

        for (uint i = 0; i < key_parts.length; i++) {
            bytes32 key_part = key_parts[i];
            add_to_merkle_tree(key_part);
            emit MTRLeafAdded(old_key_count, key_part);
        }
    }

    function add_to_merkle_tree(bytes32 value) internal {
        // Add a single leaf to the Merkle tree (update a single `branch` node)
        console.log(1);
        bytes32 node = value;
        key_count += 1;
        uint size = key_count;
        for (uint height = 0; height < TREE_DEPTH; height++) {
            if ((size & 1) == 1) {
                branch[height] = node;
                return;
            }
            node = _hash(abi.encodePacked(branch[height], node));
            size /= 2;
        }
        // As the loop should always end prematurely with the `return` statement,
        // this code should be unreachable. We assert `false` just to be safe.
        assert(false);
    }

    function get_keys_root() external view returns (bytes32) {
        bytes32 node;
        uint size = key_count;
        for (uint height = 0; height < TREE_DEPTH; height++) {
            if ((size & 1) == 1)
                node = _hash(abi.encodePacked(branch[height], node));
            else
                node = _hash(abi.encodePacked(node, zero_hashes[height]));
            size /= 2;
        }
        // IMPORTANT: default DepositContract code adds count of records in the tree
        // We don't do it here since we need a merkle tree root itself, not a hash of MTR + number of values
        return node;
    }

    function _hash(bytes memory input) internal pure returns (bytes32) {
        // IMPORTANT: deposti contract uses sha256, but it is (a) different from keccak256 and (b)
        // is not yet available in cairo (except an unwieldy example) - so we're using keccak256 here
        // return (sha256(input))
        return (keccak256(input));
    }

    function get_zerohashes() external view returns(bytes32[TREE_DEPTH] memory) {
        return (zero_hashes);
    }
}