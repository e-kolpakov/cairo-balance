import logging

from eth_typing import HexStr
from typing import List, Any, Optional, Iterable

from keccak_utils import keccak, keccak2, KeccakInput, KeccakHash
from utils import IntUtils, BytesUtils
from config import DEBUG

MerkleTreeRoot = KeccakHash

def notes():
    """
    Progressive MerkleTree https://github.com/ethereum/research/blob/master/beacon_chain_impl/progressive_merkle_tree.py
    zerohashes[i] - merkle tree root of a tree with 2**i zero elements and i height
    branch - path to the _latest_ added element. branch[i] is only read if new element is added into the right subtree
    at the i-th level. Left subtree at the i-th level is immutable (fully filled), so storing intermediate nodes is
    not needed. If added to the left subtree, zerohashes are used instead
    Tree is always 32 layers deep. zerohashes are always used

    THis equivalent to padding input to nearest power of 2 with zeroses, than calculating "naively"
    :return:
    """


class MerkleTreeNode:
    def __init__(self, label=None):
        self.label = label

    def hash(self) -> KeccakHash:
        raise NotImplemented("Must be overridden in descendents")

    def print(self, depth=0, with_hash=False):
        raise NotImplemented("Must be overridden in descendents")

    def print_hash(self):
        hash = self.hash()
        high = int.from_bytes(hash[:16], 'big', signed=False)
        low = int.from_bytes(hash[16:32], 'big', signed=False)
        return f"[high={high}, low={low}]"

    def to_cairo(self) -> HexStr:
        int_value = int.from_bytes(self.hash(), 'big', signed=False)
        return IntUtils.to_hex_str(int_value)

    def hash_hex(self) -> HexStr:
        return IntUtils.hex_str_from_bytes(self.hash(), 'big', False)

    def hash_int(self) -> int:
        return IntUtils.from_bytes(self.hash(), 'big', False)


class MerkleTreeLeafNode(MerkleTreeNode):
    def __init__(self, hash: bytes, label=None):
        super(MerkleTreeLeafNode, self).__init__(label)
        self.label = label
        self._hash = hash

    def hash(self) -> KeccakHash:
        return self._hash

    def print(self, depth=0, with_hash=False):
        padding = " " * 2 * depth
        hash_part = f", hash={self.hash_hex()}" if with_hash else ""
        return f"{padding}LeafNode({self.label}{hash_part})"

    def __str__(self):
        return f"MerkleTreeLeafNode({self.label})"


class MerkleTreeInnerNode(MerkleTreeNode):
    def __init__(self, left: MerkleTreeNode, right: MerkleTreeNode, label=None):
        super(MerkleTreeInnerNode, self).__init__(label)
        self.left = left
        self.right = right

    def hash(self) -> KeccakHash:
        return keccak2(self.left.hash(), self.right.hash())

    def print(self, depth=0, with_hash=False):
        padding = " " * 2 * depth
        hash_part = f", hash={self.hash_hex()}" if with_hash else ""
        self_print = f"{padding}Node({self.label}{hash_part})"
        left = self.left.print(depth+1, with_hash)
        right = self.right.print(depth+1, with_hash)
        return f"{self_print}\n{left}\n{right}"

    def __str__(self):
        return f"MerkleTreeInnerNode({self.label}, left={self.left.label}, right={self.right.label})"


class TopDownBuilder:
    def __init__(self, values: List[Any]):
        self._values = values

    def build(self) -> Optional[MerkleTreeNode]:
        if not self._values:
            return None

        balance_nodes = [
            MerkleTreeLeafNode(value)
            for value in self._values
        ]
        return self._build(balance_nodes)

    def _build(self, inputs: List[MerkleTreeNode]) -> Optional[MerkleTreeNode]:
        """
        The trees constructed here and in cairo must be exactly the same. So, to avoid weird bugs, 
        we're closely replicating the way it is done in cairo.
        """
        length = len(inputs)
        if length == 0:
            return None
        if length == 1:
            return inputs[0]

        center = self._div_2(length)
        left_node = self._build(inputs[:center])
        # no off-by-one here - "classical" algorithm to build a BST from a list is to do [center+1:] on the right
        # however, for the merkle tree, we don't want to exclude the "central element".
        right_node = self._build(inputs[center:])
        return MerkleTreeInnerNode(left_node, right_node)

    def _div_2(self, value):
        """
        Technically this is equivalent to just `value // 2`; however, division in cairo happens by modulo P,
        so e.g. 7 / 2 != 3. Hence, this method closely follows the way it is done in cairo - in pacticular
        `_div_2` function in merkle_tree.cairo 
        """
        if value & 0x01 == 1:
            return (value - 1) // 2
        else:
            return value // 2


class ProgressiveMerkleTreeBuilder:
    """
    Replica of https://github.com/ethereum/research/blob/master/beacon_chain_impl/progressive_merkle_tree.py
    With some modifications to be more cairo-friendly - test_merkle_tree.py ensures the result match reference
    implementation
    """
    LOGGER = logging.getLogger(__name__ + ".EthereumBuilder")
    MAX_HEIGHT = 32

    def __init__(self):
        self._zerohashes = [MerkleTreeLeafNode(b'\x00' * 32, label="zerohash0")]
        self._values = []
        for i in range(1, self.MAX_HEIGHT):
            hash_at_height = keccak(self._zerohashes[i - 1].hash() + self._zerohashes[i - 1].hash())
            self._zerohashes.append(MerkleTreeLeafNode(hash_at_height, label=f"zerohash{i}"))
        self.branch = self._zerohashes[::]

    @property
    def zerohashes(self):
        return self._zerohashes[::]

    def _hash(self, value: KeccakInput) -> KeccakHash:
        return keccak(value)

    def add_value(self, value: KeccakInput):
        self._values.append(BytesUtils.pad_to_32_multiple(value))

    def add_values(self, values: Iterable[KeccakInput]):
        for value in values:
            self.add_value(value)
        return self

    # Add a value to a Merkle tree by using the algo
    # that stores a branch of sub-roots
    def _add_value(self, value: KeccakInput, index: int) -> None:
        # See "Merkle tree leaves content" section in readme for the reasoning behind this assertion
        assert len(value) == 32, "Values should be 32 byte long"
        cur_node = MerkleTreeLeafNode(value, label=f"leaf-{index}")
        # i = 0
        # while (index + 1) % (2 ** (i + 1)) == 0:
        #     node_idx = (index + 1) // (2 ** (i + 1))
        #     cur_node = MerkleTreeInnerNode(self.branch[i], cur_node, label=f"inner-{i}-{node_idx}")
        #     i += 1

        (new_branch, at_height) = self._add_value_rec(index + 1, cur_node, 0)
        self.branch[at_height] = new_branch

    def _add_value_rec(self, index, cur_node, height=0, mask=0b1):
        if index & mask != 0:
            return (cur_node, height)

        new_node = MerkleTreeInnerNode(self.branch[height], cur_node, label=f"inner-{height}")
        return self._add_value_rec(index, new_node, height + 1, (mask * 2) + 1)

    def get_root_from_branch(self, size) -> MerkleTreeNode:
        r = MerkleTreeLeafNode(b'\x00' * 32, "zerohash0")
        return self._get_root_from_branch_rec(size, r, 0, 1)
        # for h in range(32):
        #     if (size >> h) % 2 == 1:
        #         r = MerkleTreeInnerNode(self.branch[h], r, label=f"h{h}-right")
        #     else:
        #         r = MerkleTreeInnerNode(r, self._zerohashes[h], label=f"h{h}-left")
        # return r

    def _get_root_from_branch_rec(self, size, cur_node, height, mask):
        if height == self.MAX_HEIGHT:
            return cur_node
        if size & mask == mask:
            new_node = MerkleTreeInnerNode(self.branch[height], cur_node, label=f"h{height}-branch")
            if DEBUG:
                self.LOGGER.debug(f"h{height}-branch, {new_node.hash_hex()}")
        else:
            new_node = MerkleTreeInnerNode(cur_node, self._zerohashes[height], label=f"h{height}-zerohash")
            if DEBUG:
                self.LOGGER.debug(f"h{height}-zerohash, {new_node.hash_hex()}")
        return self._get_root_from_branch_rec(size, new_node, height + 1, mask * 2)

    def get_leaves(self) -> List[KeccakInput]:
        return self._values

    def build(self) -> MerkleTreeNode:
        # Construct the tree using the branch-based algo
        for index, value in enumerate(self._values):
            self._add_value(value, index)
        # Return the root
        return self.get_root_from_branch(len(self._values))

