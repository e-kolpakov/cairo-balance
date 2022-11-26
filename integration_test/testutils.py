import argparse

import sys

import os

import json

import tempfile

from typing import TypeVar, Generic, Any, Dict, List, Optional

import logging
from starkware.cairo.sharp.sharp_client import init_client, SharpClient
import config
from src.starkware.cairo.bootloaders.generate_fact import get_program_output
from src.starkware.cairo.lang.compiler.program import Program
from utils import IntUtils

T = TypeVar('T')
S = TypeVar('S')

class CairoTestHelper(Generic[T]):
    LOGGER = logging.getLogger(__name__ + ".CairoTestHelper")

    def __init__(self, bin_dir, node_rpc_url, program, cairo_path=None):
        self.LOGGER.info(f"Initializing Cairo client")
        self.cairo_sharp_client = init_client(bin_dir=bin_dir, node_rpc_url=node_rpc_url)
        self.compile_flags = []
        if cairo_path is not None:
            self.compile_flags.append(f'--cairo_path={config.PROJECT_ROOT}')
        self.LOGGER.info(f"Compiling cairo program {program}")
        self.program = self.cairo_sharp_client.compile_cairo(source_code_path=program, flags=self.compile_flags)

    def _store_input_copy(self, program_input: Dict[str, Any], store_input_copy: str, label=""):
        filename, file_extension = os.path.splitext(store_input_copy)
        target_filename = filename if not label else f"{filename}_{label}"
        write_copy_to = f"{target_filename}{file_extension}"
        self.LOGGER.debug(f"Storing a copy of input file in {write_copy_to}")
        with open(write_copy_to, 'w') as target_file:
            json.dump(program_input, target_file, indent=4, sort_keys=True)

    def run_program(self, program_input: Dict[str, Any], label=None, store_input_copy: Optional[str]=None) -> T:
        if store_input_copy is not None:
            self._store_input_copy(program_input, store_input_copy, label)

        with tempfile.NamedTemporaryFile(mode="w") as program_input_file:
            json.dump(program_input, program_input_file, indent=4, sort_keys=True)
            program_input_file.flush()
            self.LOGGER.info(f"Running cairo program")
            cairo_pie = self.cairo_sharp_client.run_program(self.program, program_input_file.name)
            output = get_program_output(cairo_pie)
            self.LOGGER.debug(f"Cairo program run successfully - parsing output")
            result = self._parse_output(output)
        return result

    def _parse_output(self, output: List[int]) -> T:
        raise NotImplementedError


class ExampleRunnerHelper(Generic[T, S]):
    LOGGER = logging.getLogger(__name__ + ".CairoTestHelper")

    def __init__(self, cairo_runner: CairoTestHelper[S], store_input_copy: Optional[str] = None):
        self.cairo_runner = cairo_runner
        self.store_input_copy = store_input_copy

    def examples(self) -> List[T]:
        raise NotImplementedError

    def example_to_input(self, example: T) -> Dict[str, Any]:
        raise NotImplementedError

    def example_to_expected_outpiut(self, example: T) -> S:
        raise NotImplementedError

    def format_output(self, output) -> str:
        return f"{output:#x}"

    def assert_equal(self, cairo: S, expected: S) -> bool:
        return expected == cairo

    def run(self):
        has_error = False
        examples = self.examples()
        total_examples = len(examples)
        self.LOGGER.info(f"Starting verification - total {total_examples} examples")
        for (idx, (label, example)) in enumerate(examples):
            self.LOGGER.info(f"Running example {idx + 1}/{total_examples}: {label}")
            program_input = self.example_to_input(example)
            cairo_output = self.cairo_runner.run_program(program_input, label, store_input_copy=self.store_input_copy)
            expected = self.example_to_expected_outpiut(example)
            self.LOGGER.debug(
                f"Calculated:\nExpected={self.format_output(expected)}\nCairo   ={self.format_output(cairo_output)}"
            )

            if expected != cairo_output:
                has_error = True
                self.LOGGER.error(
                    f"Failed example {label}\nExpected={self.format_output(expected)}\nCairo   ={self.format_output(cairo_output)}"
                )

        if has_error:
            self.LOGGER.error("Error - one or more Merkle Tree root were different. See above for details")
            sys.exit(1)
        else:
            print("All inputs run successfully")
            sys.exit(0)


def get_arg_parser():
    parser = argparse.ArgumentParser(description="IntegrationTest ArgsParser")
    parser.add_argument(
        "--bin_dir",
        type=str,
        default="",
        help="The path to a directory that contains the cairo-compile and cairo-run scripts. "
             "If not specified, files are assumed to be in the system's PATH.",
    )
    parser.add_argument(
        "--node_rpc_url",
        type=str,
        default=config.WEB3_GOERLI_API,
        help="RPC URL to communicate with an Ethereum node on Goerli"
    )
    parser.add_argument(
        "--store_input_copy",
        type=str,
        default=None,
        help="Write a copy of cairo program_input to this file. Default: do not write a copy"
    )
    return parser