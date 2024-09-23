import unittest

from qiskit.circuit.random import random_circuit
from qiskit_ibm_runtime.fake_provider import (
    FakeAthensV2,
    FakeBelemV2,
    FakeSherbrooke,
    FakeBrisbane,
    FakeKyiv,
)

from qiskit_trebugger import Debugger
import pytest

MAX_DEPTH = 5


class TestDebuggerMock:
    """Unit tests for different IBMQ fake backends v2"""

    all_backends = [FakeAthensV2(), FakeBelemV2(), FakeSherbrooke(), FakeBrisbane(), FakeKyiv()]

    def _internal_tester(self, view, backend, num_qubits):
        for qubits in [1, num_qubits // 2, num_qubits]:
            circ = random_circuit(qubits, MAX_DEPTH, measure=True)
            debugger = Debugger()
            debugger.debug(
                circ,
                backend,
                view_type=view,
                show=False,
            )

    @pytest.mark.parametrize("backend", all_backends)
    def test_backend_v2(self, backend):
        """Backend V2 tests"""
        for view in ["jupyter"]:
            print(f"Testing with {backend.name}...")
            self._internal_tester(view, backend, backend.num_qubits)
