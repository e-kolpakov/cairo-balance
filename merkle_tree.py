from typing import List, Any, Optional

from account import Account
from keccak_utils import account_keccak, keccak2


class MerkleTreeNode:
    def hash(self):
        raise NotImplemented("Must be overridden in descendents")

    def print(self, depth):
        raise NotImplemented("Must be overridden in descendents")

    def print_hash(self, hash):
        high = int.from_bytes(hash[:16], 'big', signed=False)
        low = int.from_bytes(hash[16:32], 'big', signed=False)
        return f"[high={high}, low={low}]"

class MerkleTreeAccountLeafNode(MerkleTreeNode):
    def __init__(self, value: Account):
        self.value = value
        self._hash = account_keccak(value)
        self.left = None
        self.right = None

    def hash(self):
        return self._hash

    def print(self, depth):
        return f"BalanceLeaf({self.value}, {self.print_hash(self._hash)}) at {depth}"

class MerkleTreeInnerNode(MerkleTreeNode):
    def __init__(self, left: MerkleTreeNode, right: MerkleTreeNode):
        self.left = left
        self.right = right
        # print(f"Computing hash from {self.print_hash(left.hash())} and {self.print_hash(right.hash())}")
        self._hash = keccak2(left.hash(), right.hash())

    def hash(self):
        return self._hash

    def print(self, depth):
        self_print = f"Node({self.print_hash(self._hash)}) at {depth}"
        left = self.left.print(depth+1)
        right = self.right.print(depth+1)
        return f"{self_print}\n{left}\n{right}"


class TopDownBuilder:
    def __init__(self, values: List[Account]):
        self._values = values

    def build(self) -> Optional[MerkleTreeNode]:
        if not self._values:
            return None

        balance_nodes = [
            MerkleTreeAccountLeafNode(balance)
            for balance in self._values
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
