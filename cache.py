from __future__ import annotations

import json
import os
import logging

from typing import Union, Type, Generic, Callable, Iterable

from json_protocol import CustomJsonEncoder, CustomJsonDecoder
from utils import JsonObject, JsonObjectOrList, T


class JsonDiskCache:
    FILE_EXTENSION = "json"
    LOGGER = logging.getLogger(__name__ + ".JsonDiskCache")

    def __init__(
            self, storage_folder: str,
            encoder: Type[json.JSONEncoder] = CustomJsonEncoder,
            decoder: Type[json.JSONDecoder] = CustomJsonDecoder
    ):
        self._storage_folder = storage_folder
        self._encoder = encoder
        self._decoder = decoder

    def _make_path(self, *parts: str):
        return os.path.join(self._storage_folder, *parts) + ".json"

    def read_cache(self, *parts: str) -> JsonObject:
        raw_value = self.read_cache_raw(*parts)
        return json.loads(raw_value)

    def read_cache_raw(self, *parts: str) -> Union[str, bytes, bytearray]:
        target_path = self._make_path(*parts)
        if not os.path.exists(target_path):
            self.LOGGER.debug(f"Cache miss - {parts}")
            return "{}"

        self.LOGGER.debug(f"Cache hit - {parts}")
        with open(target_path, "r") as json_file:
            return json_file.read()

    def save_cache(self, value: JsonObjectOrList, *parts: str) -> None:
        # serialized = json.dumps(value, indent=4, sort_keys=True, cls=self._encoder)
        return self.save_cache_raw(value, *parts)

    def save_cache_raw(self, value: str, *parts: str) -> None:
        target_path = self._make_path(*parts)
        if not os.path.exists(os.path.dirname(target_path)):
            os.makedirs(os.path.dirname(target_path))

        with open(target_path, "w") as json_file:
            return json.dump(value, json_file, indent=4, sort_keys=True, cls=self._encoder)

    def clear_cache(self, *parts: str) -> None:
        path = self._make_path(*parts)
        os.remove(path)


class TypedJsonDiskCache(JsonDiskCache, Generic[T]):
    def __init__(
            self, storage_folder: str, parser: Callable[[JsonObject], T], serializer: Callable[[T], JsonObject],
            encoder: Type[json.JSONEncoder] = CustomJsonEncoder,
            decoder: Type[json.JSONDecoder] = CustomJsonDecoder
    ):
        self._parser = parser
        self._serializer = serializer
        super(TypedJsonDiskCache, self).__init__(storage_folder, encoder, decoder)

    def read_model(self, *parts: str) -> Iterable[T]:
        raw = self.read_cache(*parts)
        return (
            self._parser(record) for record in raw
        )

    def _serialize_model(self, model: T) -> JsonObject:

        return self._serializer(model)

    def save_model(self, model: T, *parts: str):
        self.save_cache(self._serialize_model(model), *parts)

    def save_models(self, models: Iterable[T], *parts: str):
        self.save_cache(
            [self._serialize_model(model) for model in models],
            *parts
        )