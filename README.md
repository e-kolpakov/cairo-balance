# Overview

## Setting up environment

**Important note:** At the time of writing this, current version of Cairo (0.10.3) works on python 3.9. Neither 
3.10 or 3.11 works (import error in one of the `cairo-lang` dependencies). Using python3.9 to install 
pipx and eth-brownie is important - you want to end up with pipx-managed `eth-brownie` virtualenv having python3.9. 

```
sudo apt-get install pytho3.9
pytho3.9 -m pip install --user pipx
pytho3.9 -m pipx ensurepath
pipx install eth-brownie
virtualenv -p python3.9 $your_virtualenv_goes_here
$your_virtualenv_goes_here/bin/activate
pip install -r requirements.txt
./inject_brownie_python_deps.sh
```

Note this actually creates **two** virtual environments: `$your_virtualenv_goes_here` and `eth-brownie`. This is 
intentional - the first one is for the "standalone" oracle + Cairo, the second one is for brownie and running tests
and scripts with contracts.

## Running

* End-to-end example (oracle + cairo + contracts): `brownie run end_to_end_example`
* Contract tests: `brownie tests`
* Oracle "integration" tests - `find oracle/integration_test/ -name "*_check.py" -exec python {} \;` 
  * Those aren't unittest/pytest/etc. tests - just a regular scripts with test semantics and assertions
* Oracle unittests: `cd oracle && python -m unittest`
  * This tests that the merkle tree implementation in python matches the "reference" implementation. Cairo and oracle
  is then tested against the python implementation.

## Project structure and locations of interest

The project uses a slightly "custom" setup, here are some noteworthy specifics:

* `oracle` folder - oracle code, executed offchain
  * `oracle/oracle.py` - a "toy" end-to-end oracle, with pluggable data "source" (where to get program input) and sink
    (where to push the updates).
  * `oracle/main.py` - an end-to-end example without pushing data to on-chain contract + multiple options to obtain 
  the input data (stub/randomly-generated/from live blockchain)
  * `oracle/config.json.example` - rename to `config.json` and fill in Web3/Eth2 API keys
  * `oracle/cairo` - contains all the Cairo code (except integration_test scripts)
  * `oracle/cairo/tlv_prover.cairo` - main entrypoint
* `ethereum` folder - contains a default brownie project structure `(`contracts` + `tests` + `scripts` + ...)
  * `TLVOracle.sol` - this is a proof-of-concept implementation of the proposed oracle code. This is a complete example,
  except necessary access control, management, etc. features.
  * `MockFactRegistry.sol` - this is a mock replica of StarkWare's FactRegistry contract. It largely exists to avoid the
  need to sync the testnet to local brownie installation (which is _very slow_).
  * `NodeOperatorRegistry.sol` - this is replica of the existing NodeOperatorRegistry contract, stripped-down of most
  of the existing functionality, but with one key addition - keeping a merkle tree of validator keys, and exposing it
  to TLVOracle (or anyone who would ask).

# Implementation assumptions

## Merkle tree algorithm

It is assumed that merkle trees are constructed using a "Progressive merkle tree"
algorithm, described in [progressive merkle tree][progressive-merkle-tree]. More detailed explanation is 
listed in the docstring of [`merkle.merkle_tree.notes`](oracle//merkle/merkle_tree.py#L12), but in short: a 32-level
deep merkle tree, with real values in the "leftmost" leaves, and assuming zeroes elsewhere. This is essentially 
equivalent to extending input to 2**32 elements and calculating Merkle Tree "naively".

If this assumption does not hold, cairo implementation (`oracle/merkle_tree.cairo`) 
and contract implementation (`contracts/contracts/NodeOperatorRegistry.sol`) will need to be updated to match 
the actual algorithm used.

**Note:** a "real" oracle will not calculate merkle trees internally (note that `oracle.py` does not use merkle tree
in any way, even through `BeaconState`) - but it is extremely helpful for debugging.

The following integration tests can be helpful:
* `oracle/tests/test_merkle_tree` - verifies that implementation in `oracle/merkle/merkle_tree.py` matches the "reference implementation".
  provided in `merkle/eth_progressive_merkle_tree_reference_impl.py`
* `oracle/integration_test/zerohashes_check.py` (and corresponding `*.cairo` file) - ensures that zerohashes computed in 
  Cairo are equal to the ones used by `oracle/merkle/merkle_tree.py`
* `oracle/integration_test/tree_check.py` (and corresponding `*.cairo` file) - ensures that trees calculated over the same data
  in cairo and in `oracle/merkle/merkle_tree.py` match.

Recommended approach to make this change is as follows:
* Replace reference implementation (`eth_merkle_tree_reference_impl.py`) with the algorithm used.
* Update (and potentially rename) `ProgressiveMerkleTreeBuilder` to make `oracle/tests/test_merkle_tree` pass
* Transfer the updated logic to Cairo (`merkle_tree.cairo`), and make `oracle/integration_test/tree_check.py` pass
  * `oracle/integration_test/zerohashes_check.py` might become obsolete.
* Make `oracle/integration_test/beacon_state_check.py` pass.

[progressive-merkle-tree]: https://github.com/ethereum/research/blob/master/beacon_chain_impl/progressive_merkle_tree.py

## Merkle tree leaves content

This is more of a shortcut, rather than assumption, but in short - cairo code becomes a lot less complex if the values
passed to Merkle tree (essentially, Merkle tree leaves) are limited to 32-byte values. This goes slightly contrary to 
the approaches actually observed "in the wild". For example in [Eth 2.0 deposit contract][eth-2-deposit-contract] 
48-byte pubkey is used as a _single_ 64-byte input to keccak hash. 

This is only a shortcut - implying 32-byte limit and splitting pubkeys/other data that exceeds 32 bytes into
multiple records somewhat simplifies Cairo code: input to the function that builds Merkle Tree can be simply a 
`List[Uint256]` (or `Uint256*` in cairo notation). It is possible to replicate the "less limiting" approach 
and allow leaves to be of arbitrary length, but it adds additional layer of complexity - the input will need to be
something like `List[List[int]]`. Such data structure cannot be directly represented in Cairo, and will involve custom
structs (e.g. `List[int]` + `List[(start_ptr, end_ptr)]`) or separator values.

Such complexity doesn't seem to add significant value, and actually precludes understanding, so I decided to go with 
the opposite approach - limiting leaf values to be 32-bytes, and splitting data that is larger than that 
(e.g. pubkeys) into multiple leaves.

The following integration tests can be helpful:
* `oracle/integration_test/mtr_leaves_check.py`  (and corresponding `.cairo` file) - checks that merkle tree inputs are
  equal between cairo implementation and python implementation.

The following code directly impacts this:
* `IntUtils.pubkey_bytes_to_keccak_input` - converts public key to keccak input, splitting the key into two 
  32-byte chunks.
* `ProgressiveMerkleTreeBuilder._add_value` - enforces the assertion
* `NodeOperatorRegistry.add_key` - performs the split in the contract

Note that currently used reference implementation and tests always use 32-byte values. If reference implementation
changes, the assumption will no longer hold, so tests in `tests/test_merkle_tree.py` might become relevant.

[eth-2-deposit-contract]: https://etherscan.io/address/0x00000000219ab540356cBB839Cbe05303d7705Fa#code

## Obtaining BeaconState merkle tree on-chain

The TLV contract will need to some means to obtain BeaconState merkle tree on-chain. [EIP-4788][eip-4788] will make
it available (somehow) to the contracts on-chain, but at the moment this mechanism is not yet implemented, or 
even accepted.

Until EIP-4788 is landed, there are multiple "workarounds" with varying cost, security and maintainance overhead,
generally revolving around keeping the merkle tree of the relevant BeaconState attributes "manually" - e.g. via a
separate trusted (ideally, first-party) oracle + periodically pushing expected BeaconState merkle tree root to an
on-chain contract. 

This approach is demonstrated in the `ethereum/scripts/end_to_end_example.py` - before running Cairo and
pushing the updated TVL to TVL contract, the oracle "syncs" the expected BeaconState to the blockchain. In a production
implementation, it will not be the part of oracle operations, and will be guarded against misuse by the contract 
(this is actually done via `onlyOwner` modifier, but a more sophisticated access control can be used).

[eip-4788]: https://eips.ethereum.org/EIPS/eip-4788
