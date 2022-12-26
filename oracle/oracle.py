import logging
from typing import Optional

from cairo import JobId, FactId
from model import ProverPayload, ProverOutput

class TVLContract:
    def update_tvl(self, prover_output: ProverOutput):
        raise NotImplementedError("Must be implemented in descendent class")


class StubTLVContract(TVLContract):
    LOGGER = logging.getLogger(__name__ + ".StubTLVContract")

    def update_tvl(self, prover_output: ProverOutput):
        self.LOGGER.info(
            f"Contract payload:\n"
            f"Parsed:{prover_output}\n"
            f"Raw:{prover_output.raw_output}"
        )


class ProverPayloadSource:
    def get_prover_payload(self) -> ProverPayload:
        raise NotImplementedError("Must be implemented in descendent class")

class Oracle:
    LOGGER = logging.getLogger(__name__ + ".Oracle")
    def __init__(self, payload_source: ProverPayloadSource, cairo_interface, contract: TVLContract, dry_run=False):
        self._payload_source = payload_source
        self._cairo_interface = cairo_interface
        self._contract = contract
        self._dry_run = dry_run

    def run_oracle(self) -> (ProverOutput, Optional[JobId], Optional[FactId]):
        payload = self._payload_source.get_prover_payload()

        prover_output = self._run_cairo(payload)
        job_id, fact_id = self._submit_cairo()
        self._wait_for_fact_registration(job_id, fact_id)

        self._update_tvl_contract(prover_output)
        return prover_output, job_id, fact_id

    def _run_cairo(self, payload: ProverPayload) -> ProverOutput:
        self.LOGGER.info("Running the cairo program")
        cairo_output = self._cairo_interface.run(payload)
        self.LOGGER.debug(f"Raw cairo output {cairo_output}")

        self.LOGGER.info("Parsing cairo output")
        try:
            prover_output = ProverOutput.read_from_prover_output(cairo_output)
        except AssertionError as e:
            self.LOGGER.exception("Couldn't parse cairo output:\n%s", cairo_output)
            raise
        self.LOGGER.debug("Cairo output %s", prover_output)

        return prover_output

    def _submit_cairo(self) -> (JobId, FactId):
        if self._dry_run:
            return None, None

        self.LOGGER.info("Submitting the program to SHARP")
        job_id = self._cairo_interface.submit()
        fact_id = self._cairo_interface.get_fact()

        return job_id, fact_id

    def _wait_for_fact_registration(self, job_id: JobId, fact_id: FactId):
        self.LOGGER.info("Submitting the program to SHARP")
        if self._dry_run:
            self.LOGGER.info("Dry-run: skipping submission")
            return

        try:
            self._cairo_interface.wait_until_fact_registered_and_valid(job_id, fact_id, timeout=30)
        except TimeoutError as exc:
            self.LOGGER.exception("Waiting for the fact timed out")
            raise

    def _update_tvl_contract(self, prover_output):
        self.LOGGER.info("Updating on-chain TVL")
        if self._dry_run:
            self.LOGGER.info("Dry-run: skipping on-chain TVL update")
            return

        self._contract.update_tvl(prover_output)


