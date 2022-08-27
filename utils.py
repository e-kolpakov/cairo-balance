from dataclasses import asdict

from datetime import date, datetime
from eth_typing import HexStr
from typing import Union, List, Dict, TypeVar
from backports import Literal

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


class IntUtils:
    @classmethod
    def to_hex_str(cls, value: int) -> HexStr:
        return HexStr(f'{value:#x}')

    @classmethod
    def from_hex_str(cls, value: HexStr) -> int:
        return int(value, 16)
