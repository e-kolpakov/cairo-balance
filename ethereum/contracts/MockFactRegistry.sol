// SPDX-License-Identifier: MIT

pragma solidity ^0.8.16;

import "../interfaces/IFactRegistry.sol";

/**
 This is a "stunt double" for StarkNet fact registry contract.
 Only exists to enable testing in "development-only" network, without syncing mainnet/Goerli
 */
contract MockFactRegistry is IFactRegistry {
    function isValid(bytes32 fact) external view returns (bool) {
        return true;
    }
}