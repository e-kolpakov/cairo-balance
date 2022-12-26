from starkware.cairo.bootloaders.generate_fact import get_program_output
from typing import List, TypeVar, Generic, Callable, Dict, Any

import tempfile

import logging
import json
import time

from starkware.cairo.bootloaders.hash_program import compute_program_hash_chain
from starkware.cairo.sharp.sharp_client import init_client

import config
from json_protocol import CustomJsonEncoder

T = TypeVar('T')

JobId = str
FactId = str


class CairoInterface(Generic[T]):
    LOGGER = logging.getLogger(__name__ + ".CairoInterface")

    def __init__(
            self,
            bin_dir: str, node_rpc_url: str, program_path: str, serializer: Callable[[T], Dict[str, Any]],
            cairo_path: str = None
    ):
        self.LOGGER.info(f"Initializing Cairo client")
        self._serializer = serializer
        self._client = init_client(bin_dir=bin_dir, node_rpc_url=node_rpc_url)
        self._program = None
        self._cairo_path = cairo_path if cairo_path else config.CAIRO_CODE_LOCATION
        self._program_path = program_path
        self._cairo_pie = None

    @property
    def program(self):
        if self._program is None:
            compile_flags = [f'--cairo_path={self._cairo_path}']
            self.LOGGER.info(f"Compiling Cairo program: {self._program_path}")
            self._program = self._client.compile_cairo(source_code_path=self._program_path, flags=compile_flags)
        return self._program

    @property
    def program_hash(self):
        return compute_program_hash_chain(self.program)

    def run(self, payload: T, store_input: str = None) -> List[int]:
        self.LOGGER.info("Serializing payload to json")
        payload = self._serializer(payload)
        program_input_serialized = json.dumps(payload, indent=4, sort_keys=True, cls=CustomJsonEncoder)

        if store_input:
            self.LOGGER.debug(f"Storing input at {store_input}")
            with open(store_input, 'w') as target_file:
                target_file.write(program_input_serialized)

        with tempfile.NamedTemporaryFile(mode="w") as program_input_file:
            program_input_file.write(program_input_serialized)
            program_input_file.flush()
            self._cairo_pie = self._client.run_program(self.program, program_input_file.name)
            self.LOGGER.debug(f"Cairo program run successfully - reading output")
            return get_program_output(self._cairo_pie)

    def submit(self) -> JobId:
        assert self._cairo_pie is not None, "Program should be run before get_fact can be called"
        job_id = self._client.submit_cairo_pie(self._cairo_pie)
        self.LOGGER.info("Submitted job id: %s", job_id)
        return job_id

    def get_fact(self) -> FactId:
        assert self._cairo_pie is not None, "Program should be run before get_fact can be called"
        return self._client.get_fact(self._cairo_pie)

    def wait_until_fact_registered_and_valid(self, job_id: JobId, fact_id: FactId, timeout: int = 300):
        self.LOGGER.info(f"Waiting for the fact {fact_id} to be registered on-chain...")
        seconds = 0.0
        # fact_registered actually checks if the fact is valid
        while not self._client.fact_registered(fact_id):
            status = self._client.get_job_status(job_id)
            self.LOGGER.debug(
                f"Elapsed: {seconds / 60} minutes. Status of job id '{job_id}' "
                f"and fact '{fact_id}' is '{status}'."
            )
            if seconds > timeout:
                message = f"Fact {fact_id} was not registered in {seconds} seconds. Status of job id '{job_id}' and fact '{fact_id}' is '{status}'."
                raise TimeoutError(message)
            time.sleep(15)
            seconds += 15
