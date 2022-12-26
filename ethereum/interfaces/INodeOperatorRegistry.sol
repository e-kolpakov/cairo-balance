// SPDX-License-Identifier: MIT

pragma solidity ^0.8.16;

interface INodeOperatorRegistry {
    function get_keys_root() external view returns (bytes32);
}