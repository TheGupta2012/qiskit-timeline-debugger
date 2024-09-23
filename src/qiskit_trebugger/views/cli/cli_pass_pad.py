"""The Transpiler Pass Pad for the CLI Debugger
"""

import curses
from collections import defaultdict
from datetime import datetime

import tabulate


class TranspilerPassPad:
    """The Transpiler Pass Pad"""

    def __init__(self, step, circuit, property_set, height, width, pad_obj):
        """Pass Pad for the CLI Debugger

        Args:
            step (TranspilationStep): The transpilation step to be displayed
            circuit (): Text circuit diagram
            property_set (default dict): The property set to be displayed
            height (int)): The height of the pad
            width (int): The width of the pad
            pad_obj (curses.Window): The curses pad object
        """
        self.transpiler_pass = step
        self.circuit = circuit
        self.property_set = property_set
        self.log_data = []
        self.height = height
        self.width = width
        self.pad = pad_obj
        self._start_row = 0

    def _get_center(self, width, string_len, divisor=2):
        """Get the center of the pad

        Args:
            width (int): The width of the pad
            string_len (int): The length of the string to be centered
            divisor (int, optional): The divisor to be used. Defaults to 2.

        """
        return max(0, int(width // divisor - string_len // 2 - string_len % 2))

    def _display_header(self, string):
        """Display a header in the pad

        Args:
            string (str): The string to be displayed
        """
        offset = self._get_center(self.width, len(string))
        self.pad.addstr(self._start_row, offset, string, curses.A_BOLD)

    def _add_title(self):
        """Add the title of the pass to the pad

        Args:
            None
        """
        pass_name = f"{self.transpiler_pass.index}. {self.transpiler_pass.name}"[
            : self.width - 1
        ]
        title_offset = self._get_center(self.width - 4, len(pass_name))
        self.pad.addstr(
            self._start_row,
            title_offset,
            pass_name,
            curses.A_BOLD,
        )
        self._start_row += 1
        self.pad.hline(self._start_row, 0, "_", self.width - 4)

    def _add_information(self):
        """Add the information of the pass to the pad

        Args:
            None
        """
        self._start_row += 2
        pass_type = self.transpiler_pass.pass_type.value
        pass_runtime = self.transpiler_pass.duration
        info_string = f"Type : {pass_type} | Runtime (ms) : {pass_runtime}"[
            : self.width - 1
        ]

        self._display_header(info_string)

    def _add_statistics(self):
        """Add the statistics of the pass to the pad

        Args:
            None
        """

        self._start_row += 2
        stats = self.transpiler_pass.circuit_stats
        props_string = (
            f"Depth : {stats.depth} | Width : {stats.width} | "
            f"Size : {stats.size} | 1Q Ops : {stats.ops_1q} | "
            f"2Q Ops : {stats.ops_2q}"[: self.width - 1]
        )

        props_string = props_string[: self.width - 1]
        props_offset = self._get_center(self.width, len(props_string))
        self.pad.addstr(self._start_row, props_offset, props_string)

    def _get_property_data(self):
        """Get the property set data as a list of lists

        Args:
            None
        """

        prop_data = []
        vf2_properties = {
            "VF2Layout_stop_reason",
            "VF2PostLayout_stop_reason",
        }

        for name, property_ in self.property_set.items():
            changed_prop = True
            if property_.prop_type not in (int, float, bool, str):
                if name in vf2_properties:
                    txt = property_.value.name
                elif name == "optimization_loop_minimum_point_state":
                    txt = f"""score : {property_.value.score}, since : {property_.value.since}"""
                elif name == "commutation_set":
                    txt = "(dict)"
                else:
                    txt = (
                        "(dict)"
                        if isinstance(property_.value, defaultdict)
                        else "(" + property_.prop_type.__name__ + ")"
                    )

            else:
                txt = str(property_.value)

            if not property_.state or len(property_.state) == 0:
                changed_prop = False
                property_.state = "---"

            data_item = [name, txt, property_.state]
            if changed_prop:
                prop_data.insert(0, data_item)
            else:
                prop_data.append(data_item)

        return prop_data

    def _add_property_set(self):
        """Add the property set to the pad

        Args:
            None
        """

        self._start_row += 2
        self._display_header("Property Set"[: self.width - 1])
        self._start_row += 1

        headers = ["Property", "Value", "State"]

        prop_data = self._get_property_data()

        prop_set_table = tabulate.tabulate(
            tabular_data=prop_data,
            headers=headers,
            tablefmt="simple_grid",
            stralign="center",
            numalign="center",
            showindex=True,
        ).splitlines()

        props_offset = self._get_center(self.width, len(prop_set_table[0]))
        for index, row in enumerate(prop_set_table):
            # 0 is default
            highlight = 0 if index > 2 else curses.A_BOLD
            self.pad.addstr(
                index + self._start_row,
                props_offset,
                row[: self.width - 1],
                highlight,
            )
        self._start_row += len(prop_set_table)

    def _add_original_qubits(self):
        """Add information about original qubit indices to the pad."""
        if "original_qubit_indices" not in self.property_set:
            return

        self._start_row += 2
        self._display_header("Original Qubit Indices"[: self.width - 1])
        self._start_row += 1

        original_indices = self.property_set["original_qubit_indices"].value.items()

        index_data = []
        for qubit, index in original_indices:
            index_data.append([qubit, index])

        headers = ["Qubit", "Index"]

        indices_table = tabulate.tabulate(
            tabular_data=index_data,
            headers=headers,
            tablefmt="simple_grid",
            stralign="center",
            numalign="center",
            showindex=False,
        ).splitlines()

        indices_offset = self._get_center(self.width, len(indices_table[0]))
        for index, row in enumerate(indices_table):
            # 0 is default
            highlight = 0 if index > 2 else curses.A_BOLD
            self.pad.addstr(
                index + self._start_row,
                indices_offset,
                row[: self.width - 1],
                highlight,
            )
        self._start_row += len(indices_table)

    def _add_layout(self, layout_type):
        """Add layout information to the pad.

        Args:
            layout_type (str): The type of layout to be added.
        """
        if (
            "original_qubit_indices" not in self.property_set
            or layout_type not in self.property_set
        ):
            return

        # total num of physical qubits
        physical_qubits = len(self.property_set["original_qubit_indices"].value)
        curr_layout = self.property_set[layout_type].value.get_physical_bits()

        # original map of qubits to indices
        original_indices = self.property_set["original_qubit_indices"].value

        # add the layout to the pad
        self._start_row += 2
        self._display_header(f"{layout_type}"[: self.width - 1])
        self._start_row += 1

        elements_per_table = 15
        # multiple tables required
        num_tables = physical_qubits // elements_per_table
        num_tables += 1 if physical_qubits % elements_per_table != 0 else 0

        for i in range(num_tables):
            start = i * elements_per_table
            end = start + elements_per_table - 1

            if start >= end:
                break

            data = [f"Physical Qubits({start}-{min(physical_qubits-1,end)})"]

            for qubit in range(start, end + 1):
                if qubit not in curr_layout:
                    data.append("--")
                    continue
                virtual_qubit = curr_layout[qubit]
                data.append(original_indices[virtual_qubit])

            # draw this single row table now
            data_table = tabulate.tabulate(
                tabular_data=[data],
                tablefmt="simple_grid",
                stralign="center",
                numalign="center",
                showindex=False,
            ).splitlines()

            table_offset = self._get_center(self.width, len(data_table[0]))
            for row, _ in enumerate(data_table):
                self.pad.addstr(
                    row + self._start_row,
                    table_offset,
                    data_table[row][: self.width - 1],
                    curses.A_BOLD,
                )
            self._start_row += len(data_table) + 1

        self._start_row += 1

    def _add_commutation_set(self):
        """Add commutation set information to the pad."""
        if "commutation_set" not in self.property_set:
            return

        # add the layout to the pad
        self._start_row += 2
        self._display_header("Commutation Set"[: self.width - 1])
        self._start_row += 1

        comm_set = self.property_set["commutation_set"].value
        comm_data_1, comm_data_2 = [], []
        for key, value in comm_set.items():
            if not isinstance(key, tuple):
                comm_data_1.append([key, value])
            else:
                comm_data_2.append([key, value])

        def _display_comm_table(data, header):
            if len(data) == 0:
                data = [[]]
            comm_table = tabulate.tabulate(
                tabular_data=data,
                headers=header,
                tablefmt="simple_grid",
                stralign="center",
                numalign="center",
                showindex=False,
                maxcolwidths=50,
            ).splitlines()

            table_offset = self._get_center(self.width, len(comm_table[0]))
            for row in range(len(comm_table)):
                self.pad.addstr(
                    row + self._start_row,
                    table_offset,
                    comm_table[row][: self.width - 1],
                )
            self._start_row += len(comm_table) + 2

        header_1 = ["Bit", "Node List"]
        header_2 = ["Node Tuple", "Set Index"]
        _display_comm_table(comm_data_1, header_1)
        _display_comm_table(comm_data_2, header_2)

    def _add_documentation(self):
        """Add the documentation to the pad

        Args:
            None
        """

        self._start_row += 2
        self._display_header("Documentation"[: self.width - 1])
        self._start_row += 1
        pass_docs = self.transpiler_pass.get_docs()

        pass_docs = (
            "    " + pass_docs if pass_docs and pass_docs.count("\n") > 0 else ""
        )
        pass_docs = [[pass_docs], [self.transpiler_pass.run_method_docs]]

        docs_table = tabulate.tabulate(
            tabular_data=pass_docs,
            tablefmt="simple_grid",
            stralign="left",
        ).splitlines()

        docs_offset = self._get_center(self.width, len(docs_table[0]))

        for idx, row in enumerate(docs_table):
            self.pad.addstr(
                idx + self._start_row,
                docs_offset,
                row[: self.width - 1],
            )
        self._start_row += len(docs_table)

    def _add_circuit(self):
        """Add the circuit diagram to the pad

        Args:
            None
        """
        self._start_row += 2
        self._display_header("Circuit Diagram"[: self.width - 1])
        self._start_row += 1
        if self.transpiler_pass.circuit_stats.depth < 300:
            # only if <300 depth, we will get a circuit to draw
            circ_string = [[self.circuit.draw(output="text", fold=100)]]
        else:
            circ_string = [
                [
                    f"Circuit depth {self.transpiler_pass.circuit_stats.depth} too large to display"
                ]
            ]
        circ_table = tabulate.tabulate(
            tabular_data=circ_string,
            tablefmt="simple_grid",
            stralign="center",
            numalign="center",
        ).splitlines()

        circ_offset = self._get_center(self.width, len(circ_table[0]))
        for index, row in enumerate(circ_table):
            self.pad.addstr(index + self._start_row, circ_offset, row)

        self._start_row += len(circ_table)

    def _add_logs(self):
        """Add the logs to the pad

        Args:
            None
        """
        self._start_row += 2
        self._display_header("Logs"[: self.width - 1])
        self._start_row += 1

        if not self.log_data:
            self.log_data = []
            for entry in self.transpiler_pass.logs:
                log_string = f"{datetime.fromtimestamp(entry.time).strftime('%H:%M:%S.%f')[:-3]} | "

                log_string += f"{entry.levelname} \n {entry.msg}" % entry.args

                self.log_data.append([log_string])
                if len(self.log_data) > 100:
                    self.log_data.append(["..."])
                    break

        if not self.log_data:
            self.log_data = [["This pass does not display any Logs."]]

        log_table = tabulate.tabulate(
            tabular_data=self.log_data,
            tablefmt="simple_grid",
            stralign="left",
            numalign="center",
        ).splitlines()

        logs_offset = self._get_center(self.width, len(log_table[0]))
        for index, row in enumerate(log_table):
            self.pad.addstr(index + self._start_row, logs_offset, row[: self.width - 1])
        self._start_row += len(log_table)

    def build_pad(self):
        """Build the pad view"""

        self._add_title()
        self._add_information()
        self._add_statistics()
        self._add_property_set()
        self._add_original_qubits()
        self._add_layout("layout")
        self._add_commutation_set()
        self._add_circuit()
        self._add_documentation()
        self._add_logs()
