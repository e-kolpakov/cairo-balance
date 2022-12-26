// SPDX-License-Identifier: MIT

pragma solidity ^0.8.16;

interface IBeaconStateMerkleTreeKeeper {
    function get_beacon_state_merkle_tree() external view returns (bytes32);
    function set_beacon_state_merkle_tree(bytes32 beaconStateMtr) external;
}