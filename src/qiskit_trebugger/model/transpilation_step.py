"""Implements a transpiler pass as a common data structure called TranspilationStep.
"""

from .circuit_stats import CircuitStats


class TranspilationStep:
    """Models a transpilation pass as a step
    with different types of properties and
    statistics
    """

    def __init__(self, name, pass_type) -> None:
        self.index = None
        self.name = name
        self.pass_type = pass_type
        self.docs = ""
        self.run_method_docs = ""
        self.duration = 0
        self.circuit_stats = CircuitStats()
        self.property_set = {}
        self.property_set_index = None
        self.logs = []
        self.dag = None

    def __repr__(self) -> str:
        return f"(name={self.name}, pass_type={self.pass_type})"

    def get_docs(self):
        """Return doc string of the pass

        Returns:
            str: docstring of the step
        """
        return self.docs
