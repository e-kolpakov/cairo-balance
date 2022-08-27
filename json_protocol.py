from __future__ import annotations

import abc
import json
from decimal import Decimal
from datetime import datetime, date

from typing import Union, List, Dict, Generic, Any

from utils import DateFormatter, T

class JsonProtocolInterface(Generic[T], abc.ABC):
    @abc.abstractmethod
    def encode(self, object: T):
        pass

    @abc.abstractmethod
    def decode(self, raw_string: str) -> T:
        pass


class DecimalJsonProtocol(JsonProtocolInterface[Decimal]):
    def encode(self, object: T):
        if not isinstance(object, Decimal):
            raise ValueError("Unsupported value")
        return str(object)

    def decode(self, raw_string: str) -> T:
        return Decimal(raw_string)


datelike = Union[date, datetime]


class DateTimeJsonProtocol(JsonProtocolInterface[datelike]):
    def encode(self, object: T):
        if not isinstance(object, (date, datetime)):
            raise ValueError("Unsupported value")
        return DateFormatter.format_datetime_iso8601(object)

    def decode(self, raw_string: str) -> T:
        if not isinstance(raw_string, str):
            raise ValueError("Unsupported value")
        return DateFormatter.parse_datetime_iso8601(raw_string)


class CustomJsonDecoder(json.JSONDecoder):
    PROTOCOLS: List[JsonProtocolInterface[Any]] = [DateTimeJsonProtocol(), DecimalJsonProtocol()]

    def __init__(self):
        super(CustomJsonDecoder, self).__init__(object_hook=self._parse)

    def _parse(self, input: Dict[str, Any]):
        return {
            key: self.apply_protocols(key, value)
            for key, value in input.items()
        }

    def apply_protocols(self, key, value):
        for custom_protocol in self.PROTOCOLS:
            try:
                return custom_protocol.decode(value)
            except:
                pass
        return value


class CustomJsonEncoder(json.JSONEncoder):
    PROTOCOLS: List[JsonProtocolInterface[Any]] = [DateTimeJsonProtocol(), DecimalJsonProtocol()]

    def default(self, obj: any):
        for custom_protocol in self.PROTOCOLS:
            try:
                return custom_protocol.encode(obj)
            except ValueError:
                continue
        return super().default(obj)