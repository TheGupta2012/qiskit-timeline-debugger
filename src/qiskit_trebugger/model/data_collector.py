"""Implements a data collector for the qiskit transpiler with a custom callback
function.
"""

from copy import deepcopy

from .pass_type import PassType
from .property import Property
from .transpilation_step import TranspilationStep


class TranspilerDataCollector:
    """Class to implement the data collector and the custom
    callback function to collect data from the qiskit
    transpiler
    """

    def __init__(self, transpilation_sequence) -> None:
        self.transpilation_sequence = transpilation_sequence
        self._properties = {}

        def callback(**kwargs):
            pass_ = kwargs["pass_"]

            pass_type = PassType.ANALYSIS if pass_.is_analysis_pass else PassType.TRANSFORMATION

            transpilation_step = TranspilationStep(pass_.name(), pass_type)
            transpilation_step.docs = pass_.__doc__
            transpilation_step.run_method_docs = getattr(pass_, "run").__doc__

            transpilation_step.duration = round(1000 * kwargs["time"], 2)

            # Properties
            property_set = kwargs["property_set"]
            _added_props = []
            _updated_props = []
            for key in property_set:
                value = property_set[key]
                if key not in self._properties.keys():
                    _added_props.append(key)
                elif (self._properties[key] is None) and (value is not None):
                    _updated_props.append(key)
                elif hasattr(value, "__len__") and (len(value) != len(self._properties[key])):
                    _updated_props.append(key)

            if len(_added_props) > 0 or len(_updated_props) > 0:
                for property_name in property_set:
                    self._properties[property_name] = property_set[property_name]

                    property_state = ""
                    if property_name in _added_props:
                        property_state = "new"
                    elif property_name in _updated_props:
                        property_state = "updated"

                    transpilation_step.property_set[property_name] = Property(
                        property_name,
                        type(property_set[property_name]),
                        property_set[property_name],
                        property_state,
                    )

            dag = deepcopy(kwargs["dag"])

            # circuit stats:
            if pass_.is_analysis_pass and len(self.transpilation_sequence.steps) > 0:
                transpilation_step.circuit_stats = self.transpilation_sequence.steps[
                    -1
                ].circuit_stats
            else:
                transpilation_step.circuit_stats.width = dag.width()
                transpilation_step.circuit_stats.size = dag.size()
                transpilation_step.circuit_stats.depth = dag.depth()

                circ_ops = {1: 0, 2: 0, 3: 0}

                for node in dag.op_nodes(include_directives=False):
                    operands_count = len(node.qargs)
                    if operands_count < 4:
                        circ_ops[operands_count] += 1

                transpilation_step.circuit_stats.ops_1q = circ_ops[1]
                transpilation_step.circuit_stats.ops_2q = circ_ops[2]
                transpilation_step.circuit_stats.ops_3q = circ_ops[3]

            # Store `dag` to use it for circuit plot generation:
            if (
                transpilation_step.pass_type == PassType.TRANSFORMATION
                and transpilation_step.circuit_stats.depth <= 300
            ):
                transpilation_step.dag = dag

            self.transpilation_sequence.add_step(transpilation_step)

        self._transpiler_callback = callback

    @property
    def transpiler_callback(self):
        """Custom callback for the transpiler

        Returns:
            function object: function handle for the callback
        """
        return self._transpiler_callback

    def show_properties(self):
        """Displays transpilation sequence properties"""
        print("Properties of transpilation sequence : ", self._properties)
