"""Implements the circuit diff functionality for quantum circuits.
"""

from numpy import uint16, zeros
from qiskit.converters import circuit_to_dag, dag_to_circuit

# make the global DP array
LCS_DP = zeros((2000, 2000), dtype=uint16)


class CircuitComparator:
    """Compares two quantum circuits and generates the
    circuit level diffs using longest common subsequences.
    """

    @staticmethod
    def get_moments(dag):
        """Returns the layers of the dag circuit as list

        Args:
            dag (DAGCircuit): DAGCircuit representing a quantum circuit

        Returns:
            List: list of depth-1 circuits as graphs
        """
        moments = [l["graph"] for l in list(dag.layers())]
        return moments

    @staticmethod
    def make_lcs(moments1, moments2):
        """Populates the LCS table by comparing the
        first circuit's layers with the second

        Args:
            moments1 (List): list of depth-1 layers
            moments2 (List): list of depth-1 layers
        """

        # clear for the base cases of dp
        for i in range(2000):
            LCS_DP[i][0], LCS_DP[0][i] = 0, 0

        size_1, size_2 = len(moments1), len(moments2)

        for i in range(1, size_1 + 1):
            for j in range(1, size_2 + 1):
                # if the layers are isomorphic then okay
                if moments1[i - 1] == moments2[j - 1]:
                    LCS_DP[i][j] = 1 + LCS_DP[i - 1][j - 1]
                else:
                    LCS_DP[i][j] = max(LCS_DP[i - 1][j], LCS_DP[i][j - 1])

    @staticmethod
    def compare(prev_circ, curr_circ):
        """Compares two circuits and returns the circuit diff as a
        quantum circuit with changed colors of diff

        Args:
            prev_circ (QuantumCircuit): first circuit
            curr_circ (QuantumCircuit): second circuit

        Returns:
            QuantumCircuit: the quantum circuit representing the
                            circuit diff
        """
        if prev_circ is None:
            return (False, curr_circ)

        # update by reference as there is no qasm now
        prev_dag = circuit_to_dag(prev_circ.copy())
        curr_dag = circuit_to_dag(curr_circ.copy())

        moments1 = CircuitComparator.get_moments(prev_dag)
        moments2 = CircuitComparator.get_moments(curr_dag)

        CircuitComparator.make_lcs(moments1, moments2)

        (size_1, size_2) = (len(moments1), len(moments2))

        id_set = set()
        i = size_1
        j = size_2

        while i > 0 and j > 0:
            if moments1[i - 1] == moments2[j - 1]:
                # just want diff for second one
                id_set.add(j - 1)
                i -= 1
                j -= 1

            else:
                if LCS_DP[i - 1][j] > LCS_DP[i][j - 1]:
                    # means the graph came from the
                    # first circuit , go up
                    i -= 1
                else:
                    # if equal or small, go left
                    j -= 1

        # if the whole circuit has not changed
        fully_changed = len(id_set) == 0

        if not fully_changed:
            for id2, layer in enumerate(list(curr_dag.layers())):
                if id2 not in id_set:
                    # this is not an LCS node -> highlight it
                    for node in layer["graph"].front_layer():
                        node.name = node.name + " "

        return (fully_changed, dag_to_circuit(curr_dag))
