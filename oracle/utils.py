from math import ceil

from dataclasses import asdict

from datetime import date, datetime
from eth_typing import HexStr
from typing import Union, List, Literal, Iterable
from keccak_utils import KeccakInput

ByteEndianness = Literal['little', 'big']
KECCAK_INPUT_LENGTH = 32

class DateFormatter:
    @staticmethod
    def parse_datetime_iso8601(raw_date: str, default_tzinfo = None) -> datetime:
        parsed = datetime.fromisoformat( raw_date)
        if not parsed.tzinfo:
            return parsed.replace(tzinfo=default_tzinfo)
        return parsed

    @staticmethod
    def parse_date_iso8601(raw_date: str) -> date:
        return date.fromisoformat(raw_date)

    @staticmethod
    def format_datetime_iso8601(date: Union[datetime, date]) -> str:
        return date.isoformat()

    @staticmethod
    def format_date_iso8601(date: Union[datetime, date]) -> str:
        return date.strftime("%Y-%m-%d")

    @staticmethod
    def set_tz(date: datetime, tz) -> datetime:
        date.replace(tzinfo=tz)
        return date


class AsDict:
    def to_dict(self):
        return asdict(self)


class BytesUtils:
    @classmethod
    def pad_to_32_multiple(cls, value: bytes, byteorder: ByteEndianness = 'big'):
        return cls.pad_to_multiple(value, 32, byteorder)
    @classmethod
    def pad_to_multiple(cls, value: bytes, multiple: int, byteorder: ByteEndianness = 'big'):
        unaligned = len(value) % multiple
        padding_length = multiple - unaligned if unaligned > 0 else 0
        padding = b'\x00' * padding_length
        if byteorder == 'big':
            return padding + value
        else:
            return value + padding
    @classmethod
    def chunks(cls, value: bytes, chunk_length: int, with_padding=False, byteorder: ByteEndianness = 'big') -> Iterable[bytes]:
        value_to_split = value if not with_padding else cls.pad_to_multiple(value, chunk_length, byteorder)
        for idx in range(0, len(value_to_split), chunk_length):
            yield value_to_split[idx:idx+chunk_length]


class IntUtils:
    MAX_SIZE = 32 * 8
    @classmethod
    def to_hex_str(cls, value: int) -> HexStr:
        return HexStr(f'{value:#x}')

    @classmethod
    def from_hex_str(cls, value: HexStr) -> int:
        return int(value, 16)

    @classmethod
    def from_bytes(cls, value: bytes, byteorder: ByteEndianness, signed=False) -> int:
        return int.from_bytes(value, byteorder, signed=signed)

    @classmethod
    def hex_str_from_bytes(cls, value: bytes, byteorder: ByteEndianness, signed=False) -> HexStr:
        return cls.to_hex_str(cls.from_bytes(value, byteorder, signed))

    @classmethod
    def to_keccak_input(cls, value: int, size_hint=32, signed=False) -> KeccakInput:
        """
        Actual output length should be multiple of 32
        """
        size = 32 * ceil(size_hint / 32)
        while size < cls.MAX_SIZE:
            try:
                return value.to_bytes(size, 'big', signed=signed)
            except OverflowError:
                # hint was wrong, let's try and find the actual size that fits
                size += 32

    @classmethod
    def slice_into_bytes(cls, value: KeccakInput, size = 32) -> List[KeccakInput]:
        pass
    @classmethod
    def read_bytes_pair_into_int(cls, high: bytes, low: bytes) -> int:
        return IntUtils.from_bytes(high + low, 'big', signed=False)

    @classmethod
    def read_pair_into_int(cls, high, low) -> int:
        return cls.read_bytes_pair_into_int(
            high=high.to_bytes(16, 'big', signed=False),
            low=low.to_bytes(16, 'big', signed=False)
        )

    @classmethod
    def read_pair_into_hex_str(cls, high, low) -> HexStr:
        hash = cls.read_pair_into_int(high, low)
        return cls.to_hex_str(hash)

    @classmethod
    def pubkey_to_keccak_input(cls, pubkey: int) -> List[KeccakInput]:
        """
        See "Merkle tree leaves content" section in readme for more details
        """
        pubkey_bytes = IntUtils.to_keccak_input(pubkey, size_hint=48)
        return cls.pubkey_bytes_to_keccak_input(pubkey_bytes)

    @classmethod
    def pubkey_bytes_to_keccak_input(cls, value: bytes) -> List[KeccakInput]:
        # "Straightforward" implementation - no limitations on leaf content
        # return value
        # "shortcut" implementation - only 32-byte values are allowed
        return list(BytesUtils.chunks(value, KECCAK_INPUT_LENGTH, with_padding=True, byteorder='big'))
