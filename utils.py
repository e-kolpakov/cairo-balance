from math import ceil

from dataclasses import asdict

from datetime import date, datetime
from eth_typing import HexStr
from typing import Union, List, Dict, TypeVar
from backports import Literal
from keccak_utils import KeccakInput

T = TypeVar('T')

JsonLiteral = Union[int, float, str, bool, None, date, datetime]
FlatJsonList = List[JsonLiteral]
FlatJsonObject = Dict[str, Union[JsonLiteral, FlatJsonList]]
_JsonObjectValue = Union[JsonLiteral, FlatJsonList, FlatJsonObject]
JsonObject = Dict[str, _JsonObjectValue]
JsonList = Union[FlatJsonList, JsonObject]
JsonObjectOrList = Union[JsonList, JsonObject]


ByteEndianness = Literal['little', 'big']

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
        next_32_multiple = 32 * ceil(32 / len(value))
        pad_bytes = next_32_multiple - len(value)
        padding = b'\x00' * pad_bytes
        if byteorder == 'big':
            return padding + value
        else:
            return value + padding


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
        :param value:
        :param size:
        :param signed:
        :return:
        """
        size = 32 * ceil(size_hint / 32)
        while size < cls.MAX_SIZE:
            try:
                return value.to_bytes(size, 'big', signed=signed)
            except OverflowError:
                # hint was wrong, let's try and find the actual size that fits
                size += 32