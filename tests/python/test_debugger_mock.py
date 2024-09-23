import unittest

from qiskit.circuit.random import random_circuit
from qiskit_ibm_runtime.fake_provider import (
    FakeAlmaden,
    FakeAlmadenV2,
    FakeAthens,
    FakeAthensV2,
    FakeBelem,
    FakeBelemV2,
    FakeKolkata,
    FakeKolkataV2,
    FakeSherbrooke,
)

from qiskit_trebugger import Debugger

MAX_DEPTH = 5


class TestDebuggerMock(unittest.TestCase):
    """Unit tests for different IBMQ fake backends v2"""

    all_backends_1 = [FakeAthens(), FakeBelem(), FakeAlmaden(), FakeKolkata()]
    all_backends_2 = [FakeAthensV2(), FakeBelemV2(), FakeAlmadenV2(), FakeKolkataV2()]

    def _internal_tester(self, view, backend, num_qubits):
        for qubits in range(1, num_qubits, 3):
            circ = random_circuit(qubits, MAX_DEPTH, measure=True)
            debugger = Debugger()
            debugger.debug(
                circ,
                backend,
                view_type=view,
                show=False,
            )

    def test_backend_v1(self):
        """Backend V2 tests"""
        for view in ["jupyter"]:
            for curr_backend in self.all_backends_1:
                print(f"Testing with {curr_backend.name()}...")
                self._internal_tester(
                    view, curr_backend, curr_backend.configuration().num_qubits
                )

    def test_backend_v2(self):
        """Backend V2 tests"""
        for view in ["jupyter"]:
            for curr_backend in self.all_backends_2:
                print(f"Testing with {curr_backend.name}...")
                self._internal_tester(view, curr_backend, curr_backend.num_qubits)
