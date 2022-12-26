# Overview

TBD

# Assumptions

## Merkle tree algorithm

It is assumed that merkle trees are constructed using a "Progressive merkle tree"
algorithm, described in [progressive merkle tree][progressive-merkle-tree]. More detailed explanation is 
listed in the docstring of [`merkle.merkle_tree.notes`](oracle//merkle/merkle_tree.py#L12), but in short: a 32-level
deep merkle tree, with real values in the "leftmost" leaves, and assuming zeroes elsewhere. This is essentially 
equivalent to extending input to 2**32 elements and calculating Merkle Tree "naively".

If this assumption does not hold, cairo implementation (`oracle/merkle_tree.cairo`) 
and contract implementation (`contracts/contracts/node_operator_registry.sol`) will need to be updated to match 
the actual algorithm used.

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

This is only a shortcut - implying 32-byte limit and splitting pubkeys/other data that does not fit into 32 bytes into
multiple records somewhat simplifies Cairo code: input to the function that builds Merkle Tree can be simply a 
`List[Uint256]` (or `Uint256*` in cairo notation). It is possible to replicate the "less limiting" approach 
and allow leaves to be of arbitrary length, but it adds an additional layer of complexity - the input will need to be
something like `List[List[int]]`. Such data structure cannot be directly represented in Cairo, and will involve custom
structs (e.g. `List[int]` + `List[(start_ptr, end_ptr)]`) or separator values.

Such complexity doesn't seem to add significant value, and actually precludes understanding of the approach, so I
decided to go with the opposite approach - limiting leaf values to be 32-bytes, and splitting data that is larger
than that (e.g. pubkeys) into multiple leaves.

The following integration tests can be helpful:
* `oracle/integration_test/mtr_leaves_check.py`  (and corresponding `.cairo` file) - checks that merkle tree inputs are
  equal between cairo implementation and python implementation.

The following code directly impacts this:
* `IntUtils.pubkey_bytes_to_keccak_input` - converts BeaconState to input to Merkle tree builder.
* `ProgressiveMerkleTreeBuilder._add_value` - enforces the assertion

Note that currently used reference implementation and tests always use 32-byte values. If reference implementation
changes, the assumption will no longer hold, so tests in `tests/test_merkle_tree.py` might become relevant.

[eth-2-deposit-contract]: https://etherscan.io/address/0x00000000219ab540356cBB839Cbe05303d7705Fa#code
