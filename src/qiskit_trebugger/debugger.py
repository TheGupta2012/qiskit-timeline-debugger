"""
Implements the main Debugger class.
Raises:
    DebuggerError: if multiple quantum circuits supplied for debugging
"""

import curses
import logging
import warnings
from typing import Optional, Union

from IPython.display import display
from qiskit import QuantumCircuit, __version__, transpile
from qiskit.providers.backend import Backend, BackendV1, BackendV2
from qiskit.transpiler.basepasses import AnalysisPass, TransformationPass
from qiskit_aer import Aer

from qiskit_trebugger.model import (
    TranspilationSequence,
    TranspilerDataCollector,
    TranspilerLoggingHandler,
)
from qiskit_trebugger.views.cli.cli_view import CLIView
from qiskit_trebugger.views.widget.timeline_view import TimelineView

from .debugger_error import DebuggerError


class Debugger:
    """Main debugger class for thr qiskit timeline debugger.

    Raises:
        DebuggerError: if multiple quantum circuits are supplied
    """

    @classmethod
    def debug(
        cls,
        circuit: QuantumCircuit,
        backend: Optional[Union[Backend, BackendV1, BackendV2]] = None,
        optimization_level: Optional[int] = 0,
        view_type: Optional[str] = "cli",
        draw_coupling_map: Optional[bool] = False,
        show: Optional[bool] = True,
        **kwargs,
    ):
        """Calls the transpile method of qiskit with the given parameters
           and populates the view of the widget with circuit diagram and
           statistics.

        Args:
            circuit (QuantumCircuit): quantum circuit to debug
            backend (Optional[Union[Backend, BackendV1, BackendV2]], optional):
                                        Quantum Backend for execution. Defaults to None.
            optimization_level (Optional[int], optional):
                                        Optimization level of transpiler. Defaults to 0.

        Raises:
            DebuggerError: if multiple quantum circuits are supplied
        """
        if view_type not in ["cli", "jupyter"]:
            raise DebuggerError("Invalid view type supplied!")

        if not isinstance(circuit, QuantumCircuit):
            raise DebuggerError("Debugger currently supports single QuantumCircuit only!")
        if backend is None:
            backend = Aer.get_backend("qasm_simulator")

        if view_type == "cli":
            if not cls._is_regular_interpreter():
                raise DebuggerError("Can not invoke CLI view in IPython or Juptyer Environment!")
            cls.view = CLIView()
        else:
            cls.view = TimelineView()

        def on_step_callback(step):
            cls.view.add_step(step)

        # Prepare the model:
        transpilation_sequence = TranspilationSequence(on_step_callback)

        if isinstance(backend, BackendV2):
            backend_name = backend.name
        else:
            backend_name = backend.name()

        warnings.simplefilter("ignore")

        transpilation_sequence.general_info = {
            "backend": backend_name,
            "optimization_level": optimization_level,
            "qiskit version": __version__,
        }

        transpilation_sequence.original_circuit = circuit

        Debugger.register_logging_handler(transpilation_sequence)
        transpiler_callback = Debugger._get_data_collector(transpilation_sequence)

        # Pass the model to the view:
        cls.view.transpilation_sequence = transpilation_sequence

        if view_type == "jupyter":
            cls.view.update_params(**kwargs)
            if show:
                display(cls.view)

        final_circ = transpile(
            circuit,
            backend,
            optimization_level=optimization_level,
            callback=transpiler_callback,
            **kwargs,
        )

        if view_type == "jupyter":
            cls.view.update_summary()
            cls.view.update_routing(final_circ, backend, draw_coupling_map)
            cls.view.update_timeline(final_circ, kwargs.get("scheduling_method", None))
            cls.view.add_class("done")
        elif view_type == "cli":
            curses.wrapper(cls.view.display)

    @classmethod
    def register_logging_handler(cls, transpilation_sequence):
        """Registers logging handlers of different transpiler passes.

        Args:
            transpilation_sequence (TranspilationSequence):
                                data structure to store the transpiler
                                passes as a sequence of transpilation
                                steps
        """

        # TODO: Do not depend on loggerDict
        all_loggers = logging.Logger.manager.loggerDict
        passes_loggers = {
            key: value
            for (key, value) in all_loggers.items()
            if key.startswith("qiskit.transpiler.passes.")
        }

        loggers_map = {}
        for _pass in AnalysisPass.__subclasses__():
            if _pass.__module__ in passes_loggers.keys():
                loggers_map[_pass.__module__] = _pass.__name__

        for _pass in TransformationPass.__subclasses__():
            if _pass.__module__ in passes_loggers.keys():
                loggers_map[_pass.__module__] = _pass.__name__

        handler = TranspilerLoggingHandler(
            transpilation_sequence=transpilation_sequence, loggers_map=loggers_map
        )
        logger = logging.getLogger("qiskit.transpiler.passes")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

    @classmethod
    def _get_data_collector(cls, transpilation_sequence):
        """Returns the data collector callback function for transpiler.

        Args:
            transpilation_sequence (list): List of transpilation steps

        Returns:
            function: Callback function for transpiler
        """
        return TranspilerDataCollector(transpilation_sequence).transpiler_callback

    @classmethod
    def _is_regular_interpreter(cls):
        """Checks if the interpreter is regular python interpreter or IPython

        Returns:
            bool: True if regular python interpreter, False otherwise
        """
        try:
            # The function get_ipython() is available on the global
            # namespace by default when IPython is started.
            _ = get_ipython().__class__.__name__

            # if this works, I am not in regular python
            # interpreter
            return False
        except NameError:
            return True
