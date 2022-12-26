import random
import secrets
import sys, os
import logging
from collections import OrderedDict
from eth_typing import HexStr

current_folder = os.path.dirname(__file__)
brownie_root = os.path.dirname(current_folder)
project_root = os.path.dirname(brownie_root)
oracle_root = os.path.join(project_root, 'oracle')

sys.path.append(oracle_root)

from api.eth_api import BeaconState, Validator
from cairo import CairoInterface
from model import ProverPayload, ProverOutput
from oracle import Oracle, ProverPayloadSource, TVLContract
import config as oracle_config
from utils import IntUtils

from brownie import accounts, NodeOperatorRegistry, TVLOracle, MockFactRegistry
from brownie.network.transaction import TransactionReceipt
from brownie import Wei

LOGGER = logging.getLogger("main")
DEBUG = True


class TVLOracleWrapper(TVLContract):
    LOGGER = logging.getLogger("main.TVLOracleWrapper")
    def __init__(self, owner, contract: TVLOracle):
        self._owner = owner
        self._contract = contract

    def get_tlv(self):
        return self._contract.get_total_value_locked()

    def _wait_for_transaction(self, tx: TransactionReceipt):
        self.LOGGER.debug(f"Transaction {tx.txid} submitted - waiting to complete")
        tx.wait(1)
        self.LOGGER.debug(f"Transaction {tx.txid} submitted - {tx.status}")
        if tx.status != 1:
            events_repr = "\n".join(str(event) for event in tx.events)
            message = f"Transaction reverted {tx.revert_msg}\n{events_repr}"
            self.LOGGER.error(message)
            raise Exception(message)
        if DEBUG:
            self._print_events(tx)

    def _print_events(self, tx):
        events_repr = "\n".join(str(event) for event in tx.events)
        self.LOGGER.debug(f"Transaction events:\n{events_repr}")

    def update_tvl(self, prover_output: ProverOutput):
        self.LOGGER.debug(f"Updating on-chain TVL\n{prover_output}")
        tx = self._contract.update_state(prover_output.raw_output)
        self._wait_for_transaction(tx)

    def update_expected_beacon_state_mtr(self, beacon_state: BeaconState):
        deploy_tx_info = {"from": self._owner}
        expected_mtr = beacon_state.merkle_tree_root().hash()

        self.LOGGER.debug(f"Updating on-chain beacon state MTR: {IntUtils.hex_str_from_bytes(expected_mtr, 'big')}")
        tx = self._contract.set_beacon_state_merkle_tree(expected_mtr, deploy_tx_info)
        self._wait_for_transaction(tx)


class ControlledChainState:
    def __init__(self, node_operator_registry: NodeOperatorRegistry, tvl_oracle: TVLOracleWrapper):
        self._all_validators = OrderedDict()
        self._lido_validator_pubkeys = []
        self._node_operator_registry = node_operator_registry
        self.tvl_oracle = tvl_oracle
        self._added_validator_keys = []

    def upsert_validator(self, key: HexStr, balance: int):
        self._all_validators[key] = balance

    def remove_validator(self, key: HexStr):
        if key in self._all_validators:
            del self._all_validators[key]

    def add_lido_validator_key(self, key: HexStr):
        if key not in self._all_validators.keys():
            raise ValueError(f"Key {key} is not in the list of all validator keys")

        self._added_validator_keys.append(key)
        self._lido_validator_pubkeys.append(key)

    # def remove_lido_validator_key(self, key: HexStr):
    #     try:
    #         self._lido_validator_pubkeys.remove(key)
    #     except ValueError as exc:
    #         pass

    def sync_beacon_state_mtr(self):
        # remove this when BeaconState mtr is available on-chain
        self.tvl_oracle.update_expected_beacon_state_mtr(self.beacon_state)

    def sync_validators(self):
        for key in self._added_validator_keys:
            key_bytes = int(key, 16).to_bytes(48, 'big', signed=False)
            self._node_operator_registry.add_key(key).wait(1)
        self._added_validator_keys = []

    @property
    def all_validators(self):
        return [
            Validator(pubkey=key, balance=balance)
            for key, balance in self._all_validators.items()
        ]

    @property
    def lido_validator_keys(self):
        return self._lido_validator_pubkeys

    @property
    def beacon_state(self) -> BeaconState:
        return BeaconState(self.all_validators)

    @property
    def lido_tlv(self):
        return sum(self._all_validators.get(key, 0) for key in self.lido_validator_keys)


class ControlledPubkeyList:
    def __init__(self):
        self._pubkeys = []

    def add(self, value):
        self._pubkeys.append(value)

    def remove(self, value):
        self._pubkeys.remove(value)

    def get_keys(self):
        return self._pubkeys


class ControlledProverPayloadSource(ProverPayloadSource):
    def __init__(self, chain_state: ControlledChainState):
        self._chain_state = chain_state

    def get_prover_payload(self) -> ProverPayload:
        return ProverPayload(
            beacon_state=self._chain_state.beacon_state,
            lido_operator_keys=self._chain_state.lido_validator_keys
        )




def deploy_contracts(owner, program_hash):
    deploy_tx_info = {"from": owner}
    node_operator_registry = NodeOperatorRegistry.deploy(owner, deploy_tx_info)
    fact_registry = MockFactRegistry.deploy(deploy_tx_info)
    tvl_oracle = TVLOracle.deploy(owner, program_hash, fact_registry.address, node_operator_registry.address, deploy_tx_info)

    return (node_operator_registry, fact_registry, tvl_oracle)


def gen_account() -> (HexStr, int):
    random_pubkey = IntUtils.hex_str_from_bytes(secrets.token_bytes(48), 'big')
    random_balance = Wei(f"{random.randint(0, 32)} ether")
    return random_pubkey, random_balance


def run_step(step_name: str, chain_state: ControlledChainState, oracle: Oracle):
    chain_state.sync_beacon_state_mtr()
    chain_state.sync_validators()
    oracle.run_oracle()  # runs the oracle and updates on-chain tvl

    assert chain_state.tvl_oracle.get_tlv() == chain_state.lido_tlv
    LOGGER.info(f"Step: {step_name} passed")

def main():
    cairo_bin_dir = ""

    owner = accounts[0]
    cairo_interface = CairoInterface(
        cairo_bin_dir, oracle_config.WEB3_GOERLI_API, oracle_config.CairoApps.TLV_PROVER,
        serializer=lambda payload: payload.to_cairo(),
    )
    program_hash = cairo_interface.program_hash

    node_operator_registry, fact_registry, tvl_oracle = deploy_contracts(owner, program_hash)

    tvl_contract_wrapper = TVLOracleWrapper(owner, tvl_oracle)

    chain_state = ControlledChainState(node_operator_registry, tvl_contract_wrapper)
    payload_source = ControlledProverPayloadSource(chain_state)
    oracle = Oracle(payload_source, cairo_interface, tvl_contract_wrapper, dry_run=False)

    # generate "initial state"
    initial_validators = [gen_account() for _ in range(3)]
    lido_validators = [initial_validators[0]]
    for key, balance in initial_validators:
        chain_state.upsert_validator(key, balance)

    for key, _balance in lido_validators:
        chain_state.add_lido_validator_key(key)

    run_step("initial", chain_state, oracle)

    additional_validators = [gen_account() for _ in range(2)]
    for key, balance in additional_validators:
        chain_state.upsert_validator(key, balance)
    run_step("updated beacon state", chain_state, oracle)

    for key, _balance in additional_validators:
        chain_state.add_lido_validator_key(key)
    run_step("added new validators", chain_state, oracle)

    update_values = random.sample(initial_validators + additional_validators, 2)
    for key, original_balance in update_values:
        new_balance = original_balance + Wei(f"{random.randint(1, 20)} ether")
        chain_state.upsert_validator(key, new_balance)
    run_step("updated validator balances", chain_state, oracle)
