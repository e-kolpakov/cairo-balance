import argparse

import sys

import os

from typing import TypeVar, Generic, Any, Dict, List, Optional

import logging
import config
from cairo import CairoInterface

T = TypeVar('T')
S = TypeVar('S')

class CairoTestHelper(Generic[T]):
    LOGGER = logging.getLogger(__name__ + ".CairoTestHelper")

    def __init__(self, bin_dir, node_rpc_url, program, cairo_path=None):
        self.cairo_interface = CairoInterface(bin_dir, node_rpc_url, program, serializer=lambda x: x, cairo_path=cairo_path)

    def _store_input_filename(self, store_input_copy: str, label="") -> str:
        filename, file_extension = os.path.splitext(store_input_copy)
        target_filename = filename if not label else f"{filename}_{label}"
        return f"{target_filename}{file_extension}"

    def run_program(self, program_input: Dict[str, Any], label=None, store_input_copy: Optional[str]=None) -> T:
        input_copy = None if store_input_copy is None else self._store_input_filename(store_input_copy, label)
        output = self.cairo_interface.run(program_input, input_copy)
        self.LOGGER.info(f"Cairo program run successfully - parsing output")
        repr_output = "\n".join(str(val) for val in output)
        self.LOGGER.debug(f"Cairo output:\n{repr_output}")
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
            self.LOGGER.error("Error - one or more examples did not match. See above for details")
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