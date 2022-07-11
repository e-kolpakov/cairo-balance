from dataclasses import dataclass


@dataclass
class Account:
    address: int
    balance: int

    def __repr__(self):
        return f"Bal({hex(self.address)}: {self.balance})"