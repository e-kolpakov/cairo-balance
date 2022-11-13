from starkware.cairo.bootloaders.generate_fact import get_program_output
from typing import List

import tempfile

import logging
import json
from starkware.cairo.sharp.sharp_client import init_client

import config
from json_protocol import CustomJsonEncoder

from model import ProverPayload

class CairoInterface:
    LOGGER = logging.getLogger(__name__ + ".JsonDiskCache")

    def __init__(self, bin_dir: str, node_rpc_url: str, program_path: str, cairo_path: str=None):
        self.LOGGER.info(f"Initializing Cairo client")
        self._client = init_client(bin_dir=bin_dir, node_rpc_url=node_rpc_url)
        self._program = None
        self._cairo_path = cairo_path if cairo_path else config.PROJECT_ROOT
        self._program_path = program_path

    @property
    def program(self):
        if self._program is None:
            compile_flags = [f'--cairo_path={self._cairo_path}']
            self.LOGGER.info(f"Compiling Cairo program: {self._program_path}")
            self._program = self._client.compile_cairo(source_code_path=self._program_path, flags=compile_flags)
        return self._program

    def run(self, payload: ProverPayload, store_input: str = None) -> List[int]:
        self.LOGGER.info("Serializing payload to json")
        program_input_serialized = json.dumps(payload.to_cairo(), indent=4, sort_keys=True, cls=CustomJsonEncoder)

        if store_input:
            self.LOGGER.debug(f"Storing input at {store_input}")
            with open(store_input, 'w') as target_file:
                target_file.write(program_input_serialized)

        with tempfile.NamedTemporaryFile(mode="w") as program_input_file:
            program_input_file.write(program_input_serialized)
            program_input_file.flush()
            cairo_pie = self._client.run_program(self.program, program_input_file.name)
            self.LOGGER.debug(f"Cairo program run successfully - reading output")
            return get_program_output(cairo_pie)
