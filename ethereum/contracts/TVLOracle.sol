// SPDX-License-Identifier: MIT

pragma solidity ^0.8.16;

import "../interfaces/IFactRegistry.sol";
import "../interfaces/INodeOperatorRegistry.sol";
import "../interfaces/IBeaconStateMerkleTreeKeeper.sol";
import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/utils/math/SafeMath.sol";


contract TVLOracle is IBeaconStateMerkleTreeKeeper {
    // IBeaconStateMerkleTreeKeeper - see comment in _get_beacon_state_mtr
    using SafeMath for uint256;

    uint256 constant MAX_16_BYTE_VALUE = 2 ** (16*8) - 1;

    uint256 totalValueLocked;

    // The Cairo program hash.
    uint256 cairoProgramHash;

    // The Cairo verifier.
    IFactRegistry cairoVerifier;

    // Node registry constract
    INodeOperatorRegistry nodeRegistry;

    address owner;
    bytes32 expectedBeaconStateMtr;

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }

    // this even is for debugging purposes only
    event ReconstructedKeccak(
        string name,
        bytes32 reconstructed,
        uint256 high,
        uint256 low
    );

    /*
      Initializes the contract state.
    */
    constructor(
        address owner_,
        uint256 cairoProgramHash_,
        address cairoVerifier_,
        address nodeRegistry_
    ) {
        owner = owner_;
        cairoProgramHash = cairoProgramHash_;
        cairoVerifier = IFactRegistry(cairoVerifier_);
        nodeRegistry = INodeOperatorRegistry(nodeRegistry_);
    }

    // technically this should be internal, but in such case it is not available in tests - so taking a little shortcut here
    function reconstruct_keccak_from_program_output(uint256 high, uint256 low) pure public returns (bytes32) {
        assert(low <= MAX_16_BYTE_VALUE);
        assert(high <= MAX_16_BYTE_VALUE);
        // return bytes32(low);
        uint256 shifted_high = high << (16*8);
        return bytes32(shifted_high + low);
        // return bytes32(shifted_high + low);
    }

    function update_state(uint256[] memory programOutput) public {
        require(programOutput.length == 5);

        // ensure merkle tree roots are encoded correctly - cairo outputs uint256
        // as TWO values (high, low) - see serialize_uint256 function in model.cairo
        require(programOutput[0] <= MAX_16_BYTE_VALUE, "Program output out of range");
        require(programOutput[1] <= MAX_16_BYTE_VALUE, "Program output out of range");
        require(programOutput[2] <= MAX_16_BYTE_VALUE, "Program output out of range");
        require(programOutput[3] <= MAX_16_BYTE_VALUE, "Program output out of range");

        // ensure beacon state mtr is correct
        bytes32 beaconStateMtr = reconstruct_keccak_from_program_output(programOutput[0], programOutput[1]);
        emit ReconstructedKeccak(
            "beacon_state", beaconStateMtr, programOutput[0], programOutput[1]
        );
        require(beaconStateMtr == expectedBeaconStateMtr, "Beacon State Merkle Tree root did not match");

        // ensure validator list mtr is correct
        bytes32 validatorListMtr = reconstruct_keccak_from_program_output(programOutput[2], programOutput[3]);
        emit ReconstructedKeccak(
            "lido_validators", validatorListMtr, programOutput[2], programOutput[3]
        );
        bytes32 expectedValidatorListMtr = nodeRegistry.get_keys_root();
        require(validatorListMtr == expectedValidatorListMtr, "Lido validator keys Merkle Tree root did not match");

        // Ensure that a corresponding proof was verified.
        bytes32 outputHash = keccak256(abi.encodePacked(programOutput));
        bytes32 fact = keccak256(abi.encodePacked(cairoProgramHash, outputHash));
        require(cairoVerifier.isValid(fact), "MISSING_CAIRO_PROOF");

        // all checks passed, update the TVL
        totalValueLocked = programOutput[4];
    }

    function get_total_value_locked() external view returns (uint256) {
        return totalValueLocked;
    }

    

    function get_beacon_state_merkle_tree() external view returns (bytes32) {
        // When BeaconState MTR is available on-chain, this will just return that
        // for now, this is managed in the contract itself, but could be externalized
        return (expectedBeaconStateMtr);
    }

    function set_beacon_state_merkle_tree(bytes32 beaconStateMtr) external onlyOwner {
        // When BeaconState MTR is available on-chain, this will just return that
        // for now, this is managed in the contract itself, but could be externalized
        expectedBeaconStateMtr = beaconStateMtr;
    }
}