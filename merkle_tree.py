import logging

from eth_typing import HexStr
from typing import List, Any, Optional

from keccak_utils import keccak, keccak2, KeccakInput, KeccakHash
from utils import IntUtils, BytesUtils

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


class MerkleTreeLeafNode(MerkleTreeNode):
    def __init__(self, hash: bytes, label=None):
        self.label = label
        self._hash = hash

    def hash(self) -> KeccakHash:
        return self._hash

    def print(self, depth=0, with_hash=False):
        padding = " " * 2 * depth
        hash_part = f", hash={self.hash_hex()}" if with_hash else ""
        return f"{padding}LeafNode({self.label}{hash_part})"


class MerkleTreeInnerNode(MerkleTreeNode):
    def __init__(self, left: MerkleTreeNode, right: MerkleTreeNode, label=None):
        self.label = label
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
        return f"{left}\n{right}\n{self_print}\n"


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


class EthereumBuilder:
    """
    Replica of https://github.com/ethereum/research/blob/master/beacon_chain_impl/progressive_merkle_tree.py
    """
    LOGGER = logging.getLogger(__name__ + ".EthereumBuilder")
    def __init__(self):
        self._zerohashes = [MerkleTreeLeafNode(b'\x00' * 32, label="zerohash0")]
        self._values = []
        for i in range(1, 32):
            hash_at_height = keccak(self._zerohashes[i - 1].hash() + self._zerohashes[i - 1].hash())
            self._zerohashes.append(MerkleTreeLeafNode(hash_at_height, label=f"zerohash{i}"))
        self.branch = self._zerohashes[::]

    @property
    def zerohashes(self):
        return self._zerohashes[::]

    def _hash(self, value: KeccakInput) -> KeccakHash:
        return keccak(value)

    def add_value(self, value: bytes):
        self._values.append(BytesUtils.pad_to_32_multiple(value))

    def add_values(self, values: List[bytes]):
        for value in values:
            self.add_value(value)

    # Add a value to a Merkle tree by using the algo
    # that stores a branch of sub-roots
    def _add_value(self, index: int, value: KeccakInput) -> None:
        i = 0
        cur_node = MerkleTreeLeafNode(value, label=f"leaf-{index}")
        while (index + 1) % 2 ** (i + 1) == 0:
            i += 1
        for j in range(0, i):
            cur_node = MerkleTreeInnerNode(self.branch[j], cur_node, label=f"inner-{j}")
        self.branch[i] = cur_node

    def get_root_from_branch(self, size) -> MerkleTreeNode:
        r = MerkleTreeLeafNode(b'\x00' * 32, "zerohash0")
        for h in range(32):
            if (size >> h) % 2 == 1:
                r = MerkleTreeInnerNode(self.branch[h], r, label=f"h{h}-right")
            else:
                r = MerkleTreeInnerNode(r, self._zerohashes[h], label=f"h{h}-left")
        return r

    def build(self) -> MerkleTreeNode:
        # Construct the tree using the branch-based algo
        for index, value in enumerate(self._values):
            self._add_value(index, value)
        # Return the root
        return self.get_root_from_branch(len(self._values))