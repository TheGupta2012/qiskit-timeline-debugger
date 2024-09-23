"""A module for the CLI view for the Qiskit Transpiler Debugger.
"""

import curses
from curses.textpad import Textbox

import tabulate
from qiskit.converters import dag_to_circuit
from qiskit.dagcircuit import DAGCircuit

from ...model.pass_type import PassType
from .cli_pass_pad import TranspilerPassPad
from .config import COLORS


class CLIView:
    """A class representing the CLI view for the Qiskit Transpiler Debugger."""

    def __init__(self):
        """Initialize the CLIView object."""
        self._title = None
        self._overview = None

        self._all_passes_data = []
        self._all_passes_table = None
        self._pass_table_headers = [
            "Pass Name",
            "Pass Type",
            "Runtime (ms)",
            "Depth",
            "Size",
            "1q Gates",
            "2q Gates",
            "Width",
        ]
        # add the whitespace option
        tabulate.PRESERVE_WHITESPACE = True

        self._all_passes_pad = None
        self._pass_pad_list = None
        self._status_bar = None
        self._title_string = "Qiskit Transpiler Debugger"

        self._status_strings = {
            "normal": " STATUS BAR  | Arrow keys: Scrolling | 'U/D': Page up/down |"
            " 'I': Index into a pass | 'H': Toggle overview | 'Q': Exit",
            "index": " STATUS BAR  | Enter the index of the pass you want to view : ",
            "invalid": " STATUS BAR  | Invalid input entered. Press Enter to continue.",
            "out_of_bounds": " STATUS BAR  | Number entered is out of bounds."
            " Press Enter to continue.",
            "pass": " STATUS BAR  | Arrow keys: Scrolling | 'U/D': Page up/down |"
            " 'N/P': Move to next/previous | 'I': Index into a pass |"
            " 'B': Back to home | 'Q': Exit",
        }

        self._colors = {
            "title": None,
            "status": None,
            "base_pass_title": None,
            "changing_pass": None,
        }

        # define status object
        self._reset_view_params()

        # add the transpilation sequence
        self.transpilation_sequence = None

    def _reset_view_params(self):
        """Reset the view parameters to their default values."""

        self._view_params = {
            "curr_row": 0,
            "curr_col": 0,
            "last_width": 0,
            "last_height": 0,
            "pass_id": -1,
            "transpiler_pad_width": 800,
            "transpiler_pad_height": 5000,
            "transpiler_start_row": 6,
            "transpiler_start_col": None,
            "status_type": "normal",
            "overview_visible": True,
            "overview_change": False,
        }

    def _init_color(self):
        """Initialize colors for the CLI interface."""
        # Start colors in curses
        curses.start_color()

        curses.init_pair(1, COLORS.TITLE["front"], COLORS.TITLE["back"])
        curses.init_pair(2, COLORS.STATUS["front"], COLORS.STATUS["back"])
        curses.init_pair(3, COLORS.BASE_PASSES_TITLE["front"], COLORS.BASE_PASSES_TITLE["back"])
        curses.init_pair(4, COLORS.CHANGING_PASS["front"], COLORS.CHANGING_PASS["back"])

        self._colors["title"] = curses.color_pair(1)
        self._colors["status"] = curses.color_pair(2)
        self._colors["base_pass_title"] = curses.color_pair(3)
        self._colors["changing_pass"] = curses.color_pair(4)

    def _get_center(self, width, string_len, divisor=2):
        """Calculate the starting position for centering a string.

        Args:
            width (int): Total width of the container.
            string_len (int): Length of the string to be centered.
            divisor (int, optional): Divisor for the centering calculation. Defaults to 2.

        Returns:
            int: Starting position for centering the string.
        """
        return max(0, int(width // divisor - string_len // 2 - string_len % 2))

    def _handle_keystroke(self, key):
        """Handle the keystrokes for navigation within the CLI interface.

        Args:
            key (int): The key pressed by the user.

        Returns:
            None
        """
        if key == curses.KEY_UP:
            self._view_params["curr_row"] -= 1
            self._view_params["curr_row"] = max(self._view_params["curr_row"], 0)
        elif key == curses.KEY_LEFT:
            self._view_params["curr_col"] -= 1
        elif key == curses.KEY_DOWN:
            self._view_params["curr_row"] += 1
            if self._view_params["status_type"] == "normal":
                self._view_params["curr_row"] = min(
                    self._view_params["curr_row"], len(self._all_passes_table) - 1
                )
            elif self._view_params["status_type"] in ["index", "pass"]:
                self._view_params["curr_row"] = min(
                    self._view_params["curr_row"],
                    1999,
                )

        elif key == curses.KEY_RIGHT:
            self._view_params["curr_col"] += 1

            if self._view_params["status_type"] == "normal":
                self._view_params["curr_col"] = min(
                    self._view_params["curr_col"], len(self._all_passes_table[1]) - 1
                )

            elif self._view_params["status_type"] in ["index", "pass"]:
                self._view_params["curr_col"] = min(
                    self._view_params["curr_col"],
                    curses.COLS - self._view_params["transpiler_start_col"] - 1,
                )
        elif key in [ord("u"), ord("U")]:
            self._view_params["curr_row"] = max(self._view_params["curr_row"] - 10, 0)

        elif key in [ord("d"), ord("D")]:
            self._view_params["curr_row"] += 10
            if self._view_params["status_type"] == "normal":
                self._view_params["curr_row"] = min(
                    self._view_params["curr_row"], len(self._all_passes_table) - 1
                )
            elif self._view_params["status_type"] in ["index", "pass"]:
                self._view_params["curr_row"] = min(
                    self._view_params["curr_row"],
                    1999,
                )

        elif key in [ord("i"), ord("I")]:
            # user wants to index into the pass
            self._view_params["status_type"] = "index"

        elif key in [ord("n"), ord("N")]:
            if self._view_params["status_type"] in ["index", "pass"]:
                self._view_params["pass_id"] = min(
                    self._view_params["pass_id"] + 1,
                    len(self.transpilation_sequence.steps) - 1,
                )
                self._view_params["status_type"] = "pass"

        elif key in [ord("p"), ord("P")]:
            if self._view_params["status_type"] in ["index", "pass"]:
                self._view_params["pass_id"] = max(0, self._view_params["pass_id"] - 1)
                self._view_params["status_type"] = "pass"

        elif key in [ord("b"), ord("B")]:
            # reset the required state variables
            self._view_params["status_type"] = "normal"
            self._view_params["pass_id"] = -1
            self._view_params["curr_col"] = 0
            self._view_params["curr_row"] = 0

        elif key in [ord("h"), ord("H")]:
            self._view_params["overview_visible"] = not self._view_params["overview_visible"]
            self._view_params["overview_change"] = True
            self._view_params["curr_col"] = 0
            self._view_params["curr_row"] = 0
            if not self._view_params["overview_visible"]:
                self._view_params["transpiler_start_col"] = 0

    def _build_title_win(self, cols):
        """Builds the title window for the debugger

        Args:
            cols (int): width of the window

        Returns:
            title_window (curses.window): title window object
        """
        title_rows = 4
        title_cols = cols
        begin_row = 1
        title_window = curses.newwin(title_rows, title_cols, begin_row, 0)

        title_str = self._title_string[: title_cols - 1]

        # Add title string to the title window
        start_x_title = self._get_center(title_cols, len(title_str))
        title_window.bkgd(self._colors["title"])
        title_window.hline(0, 0, "-", title_cols)
        title_window.addstr(1, start_x_title, title_str, curses.A_BOLD)
        title_window.hline(2, 0, "-", title_cols)

        # add Subtitle
        subtitle = "| "
        for key, value in self.transpilation_sequence.general_info.items():
            subtitle += f"{key}: {value} | "

        subtitle = subtitle[: title_cols - 1]
        start_x_subtitle = self._get_center(title_cols, len(subtitle))
        title_window.addstr(3, start_x_subtitle, subtitle)

        return title_window

    def _get_overview_stats(self):
        """Get the overview statistics for the transpilation sequence.

        Returns:
            dict: A dictionary containing overview statistics for the transpilation sequence.
        """
        init_step = self.transpilation_sequence.steps[0]
        final_step = self.transpilation_sequence.steps[-1]

        # build overview
        overview_stats = {
            "depth": {"init": 0, "final": 0},
            "size": {"init": 0, "final": 0},
            "width": {"init": 0, "final": 0},
        }

        # get the depths, size and width
        init_step_dict = init_step.circuit_stats.__dict__
        final_step_dict = final_step.circuit_stats.__dict__

        for (
            prop,
            value,
        ) in overview_stats.items():  # prop should have same name as in CircuitStats
            value["init"] = init_step_dict[prop]
            value["final"] = final_step_dict[prop]

        # get the op counts
        overview_stats["ops"] = {"init": 0, "final": 0}
        overview_stats["ops"]["init"] = (
            init_step.circuit_stats.ops_1q
            + init_step.circuit_stats.ops_2q
            + init_step.circuit_stats.ops_3q
        )

        overview_stats["ops"]["final"] = (
            final_step.circuit_stats.ops_1q
            + final_step.circuit_stats.ops_2q
            + final_step.circuit_stats.ops_3q
        )

        return overview_stats

    def _build_overview_win(self, rows, cols):
        """Build and return the overview window for the debugger.

        Args:
            rows (int): Height of the window.
            cols (int): Width of the window.

        Returns:
            curses.window: The overview window object.
        """
        begin_row = 6
        overview_win = curses.newwin(rows, cols, begin_row, 0)

        total_passes = {"T": 0, "A": 0}
        for step in self.transpilation_sequence.steps:
            if step.pass_type == PassType.TRANSFORMATION:
                total_passes["T"] += 1
            else:
                total_passes["A"] += 1

        total_pass_str = f"Total Passes : {total_passes['A'] + total_passes['T']}"[: cols - 1]
        pass_categories_str = (
            f"Transformation : {total_passes['T']} | Analysis : {total_passes['A']}"[: cols - 1]
        )

        start_x = 5
        overview_win.addstr(5, start_x, "Pass Overview"[: cols - 1], curses.A_BOLD)
        overview_win.addstr(6, start_x, total_pass_str)
        overview_win.addstr(7, start_x, pass_categories_str)

        # runtime
        runtime_str = f"Runtime : {round(self.transpilation_sequence.total_runtime,2)} ms"[
            : cols - 1
        ]
        overview_win.addstr(9, start_x, runtime_str, curses.A_BOLD)

        # circuit stats
        headers = ["Property", "Initial", "Final"]

        overview_stats = self._get_overview_stats()
        rows = []
        for prop, value in overview_stats.items():
            rows.append([prop.capitalize(), value["init"], value["final"]])
        stats_table = tabulate.tabulate(
            rows,
            headers=headers,
            tablefmt="simple_grid",
            stralign=("center"),
            numalign="center",
        ).splitlines()

        for row in range(12, 12 + len(stats_table)):
            overview_win.addstr(row, start_x, stats_table[row - 12][: cols - 1])

        # for correct formatting of title
        max_line_length = len(stats_table[0])

        # add titles

        # stats header
        stats_str = "Circuit Statistics"[: cols - 1]
        stats_head_offset = self._get_center(max_line_length, len(stats_str))
        overview_win.addstr(11, start_x + stats_head_offset, stats_str, curses.A_BOLD)

        # overview header
        overview_str = "TRANSPILATION OVERVIEW"[: cols - 1]
        start_x_overview = start_x + self._get_center(max_line_length, len(overview_str))
        overview_win.hline(0, start_x, "_", min(cols, max_line_length))
        overview_win.addstr(2, start_x_overview, overview_str, curses.A_BOLD)
        overview_win.hline(3, start_x, "_", min(cols, max_line_length))

        # update the dimensions
        self._view_params["transpiler_start_col"] = start_x + max_line_length + 5
        return overview_win

    def _get_pass_title(self, cols):
        """Get the window object for the title of the pass table.

        Args:
            cols (int): Width of the window.

        Returns:
            curses.window: The window object for the pass title.
        """
        height = 4

        width = max(5, cols - self._view_params["transpiler_start_col"] - 1)
        pass_title = curses.newwin(
            height,
            width,
            self._view_params["transpiler_start_row"],
            self._view_params["transpiler_start_col"],
        )
        # add the title of the table
        transpiler_passes = "Transpiler Passes"[: cols - 1]
        start_header = self._get_center(width, len(transpiler_passes))
        try:
            pass_title.hline(0, 0, "_", width - 4)
            pass_title.addstr(2, start_header, "Transpiler Passes", curses.A_BOLD)
            pass_title.hline(3, 0, "_", width - 4)
        except Exception as _:
            pass_title = None

        return pass_title

    def _get_statusbar_win(self, rows, cols, status_type="normal"):
        """Returns the status bar window object

        Args:
            rows (int): Current height of the terminal
            cols (nt): Current width of the terminal
            status_type (str, optional): Type of status of the debugger. Corresponds to
                                         different view states of the debugger.
                                         Defaults to "normal".

            STATUS STATES
                -normal        : normal status bar
                -index         : index status bar - user is entering the numbers
                                 (requires input to be shown to user)
                -invalid       : error status bar - user has entered an invalid character
                -out_of_bounds : out of bounds status bar - user has entered a number out of bounds
                -pass          : pass status bar - user has entered a valid number and is now
                                 viewing the pass details

                NOTE : processing is done after the user presses enter.
                This will only return a status bar window, TEXT processing is done within
                this function ONLY
        Returns:
            curses.window : Statusbar window object
        """

        status_str = self._status_strings[status_type][: cols - 1]

        statusbar_window = curses.newwin(1, cols, rows - 1, 0)
        statusbar_window.bkgd(" ", self._colors["status"])

        offset = 0
        statusbar_window.addstr(0, offset, status_str)
        offset += len(status_str)

        # now if index, enter a text box
        if status_type == "index":
            textbox = Textbox(statusbar_window)
            textbox.edit()
            str_value = textbox.gather().split(":")[1].strip()  # get the value of the entered text

            try:
                num = int(str_value)
                total_passes = len(self.transpilation_sequence.steps)
                if num >= total_passes or num < 0:
                    status_str = self._status_strings["out_of_bounds"]
                else:
                    status_str = self._status_strings["pass"]
                    self._view_params["pass_id"] = num
            except ValueError as _:
                # Invalid number entered
                status_str = self._status_strings["invalid"]
            status_str = status_str[: cols - 1]

            # display the new string
            statusbar_window.clear()
            offset = 0
            statusbar_window.addstr(0, 0, status_str)
            offset += len(status_str)

        statusbar_window.addstr(0, offset, " " * (cols - offset - 1))

        return statusbar_window

    def _refresh_base_windows(self, resized, height, width):
        """Refreshes the base windows of the debugger

        Args:
            width (int): Current width of the terminal

        Returns:
            None
        """
        if resized:
            self._title = self._build_title_win(width)
            self._title.noutrefresh()

        overview_toggle = (
            self._view_params["overview_visible"] and self._view_params["overview_change"]
        )
        if resized or overview_toggle:
            try:
                self._overview = self._build_overview_win(height, width)
                self._overview.noutrefresh()
            except Exception as _:
                # change the view param for overview
                self._view_params["transpiler_start_col"] = 0

        pass_title_window = self._get_pass_title(width)
        if pass_title_window:
            pass_title_window.noutrefresh()

    def _get_pass_circuit(self, step):
        if step.pass_type == PassType.TRANSFORMATION:
            if step.circuit_stats.depth > 300:
                # means it had depth > 300, so we can't show it
                return None
            return dag_to_circuit(step.dag)
        idx = step.index
        # Due to a bug in DAGCircuit.__eq__, we can not use ``step.dag != None``

        found_transform = False
        while not isinstance(self.transpilation_sequence.steps[idx].dag, DAGCircuit) and idx > 0:
            idx = idx - 1
            if idx >= 0:
                found_transform = (
                    self.transpilation_sequence.steps[idx].pass_type == PassType.TRANSFORMATION
                )

        if not found_transform:
            return self.transpilation_sequence.original_circuit

        return dag_to_circuit(self.transpilation_sequence.steps[idx].dag)

    def _get_pass_property_set(self, step):
        if step.property_set_index is not None:
            return self.transpilation_sequence.steps[step.property_set_index].property_set

        return {}

    def _build_pass_pad(self, index):
        step = self.transpilation_sequence.steps[index]
        pad = curses.newpad(
            self._view_params["transpiler_pad_height"],
            self._view_params["transpiler_pad_width"],
        )
        pass_pad = TranspilerPassPad(
            step,
            self._get_pass_circuit(step),
            self._get_pass_property_set(step),
            self._view_params["transpiler_pad_height"],
            self._view_params["transpiler_pad_width"],
            pad,
        )
        pass_pad.build_pad()
        self._pass_pad_list[index] = pass_pad.pad

    def add_step(self, step):
        """Adds a step to the transpilation sequence.

        Args:
            step (TranspilationStep): `TranspilationStep` object to be added to the
                                      transpilation sequence.
        """
        self._all_passes_data.append(
            [
                step.name,
                step.pass_type.value,
                step.duration,
                step.circuit_stats.depth,
                step.circuit_stats.size,
                step.circuit_stats.ops_1q,
                step.circuit_stats.ops_2q,
                step.circuit_stats.width,
            ]
        )

    def _get_all_passes_table(self):
        """Generate and return the table containing all the transpiler passes.

        Returns:
            list: The list representing the table of all transpiler passes.
        """
        # build from the transpilation sequence
        # make table
        pass_table = tabulate.tabulate(
            headers=self._pass_table_headers,
            tabular_data=self._all_passes_data,
            tablefmt="simple_grid",
            stralign="center",
            numalign="center",
            showindex="always",
        ).splitlines()

        return pass_table

    def _get_changing_pass_list(self):
        """Get the list of indices of passes that caused a change in the circuit.

        Returns:
            list: A list containing the indices of changing passes.
        """
        pass_id_list = []
        for i in range(1, len(self.transpilation_sequence.steps)):
            prev_step = self.transpilation_sequence.steps[i - 1]
            curr_step = self.transpilation_sequence.steps[i]
            if prev_step.circuit_stats != curr_step.circuit_stats:
                pass_id_list.append(i)
        return pass_id_list

    def _get_all_passes_pad(self):
        """Generate and return the pad containing all the transpiler passes.

        Returns:
            curses.pad: The pad containing all the transpiler passes.
        """
        start_x = 4
        table_width = 500  # for now
        table_height = len(self._all_passes_table) + 1
        pass_pad = curses.newpad(table_height, table_width)

        header_height = 3

        # centering is required for each row
        for row in range(header_height):
            offset = self._get_center(
                table_width, len(self._all_passes_table[row][: table_width - 1])
            )
            pass_pad.addstr(
                row,
                start_x + offset,
                self._all_passes_table[row][: table_width - 1],
                curses.A_BOLD | self._colors["base_pass_title"],
            )

        # generate a changing pass set to see which pass
        # changed the circuit and which didn't
        changing_pass_list = set(self._get_changing_pass_list())

        def _is_changing_pass_row(row):
            # dashes only at even rows
            if row % 2 == 0:
                return False
            index = (row - header_height) // 2
            if index in changing_pass_list:
                return True
            return False

        # now start adding the passes
        for row in range(header_height, len(self._all_passes_table)):
            offset = self._get_center(
                table_width, len(self._all_passes_table[row][: table_width - 1])
            )
            highlight = 0

            if _is_changing_pass_row(row):
                highlight = curses.A_BOLD | self._colors["changing_pass"]

            pass_pad.addstr(
                row,
                start_x + offset,
                self._all_passes_table[row][: table_width - 1],
                highlight,
            )

        # populated pad with passes
        return pass_pad

    def _render_transpilation_pad(self, pass_pad, curr_row, curr_col, rows, cols):
        """Function to render the pass pad.

        NOTE : this is agnostic of whether we are passing the base pad
            or the individual transpiler pass pad. Why?
            Because we are not shifting the pad, we are just refreshing it.

        Args:
            pass_pad (curses.pad): The pad containing the individual pass details.
            curr_row (int): Current row position.
            curr_col (int): Current column position.
            rows (int): Total number of rows in the terminal.
            cols (int): Total number of columns in the terminal.

        Returns:
            None
        """
        if not pass_pad:
            return

        # 4 rows for the title + curr_row (curr_row is the row of the pass)
        title_height = 5
        start_row = self._view_params["transpiler_start_row"] + title_height

        # if we don't have enough rows
        if start_row >= rows - 2:
            return

        # if we don't have enough columns
        if self._view_params["transpiler_start_col"] >= cols - 6:
            return

        actual_width = pass_pad.getmaxyx()[1]
        window_width = cols - self._view_params["transpiler_start_col"]
        col_offset = (actual_width - window_width) // 2

        pass_pad.noutrefresh(
            curr_row,
            col_offset + curr_col,
            start_row,
            self._view_params["transpiler_start_col"],
            rows - 2,
            cols - 6,
        )

    def _pre_input(self, height, width):
        """Function to render the pad before any input is entered
           by the user

        Args:
            height (int): Number of rows
            width (int): Number of cols
        """
        pad_to_render = None

        if self._view_params["status_type"] == "index":
            pass_id = self._view_params["pass_id"]
            if pass_id == -1:
                pad_to_render = self._all_passes_pad
            else:
                if self._pass_pad_list[pass_id] is None:
                    self._build_pass_pad(pass_id)
                pad_to_render = self._pass_pad_list[pass_id]

            self._render_transpilation_pad(
                pad_to_render,
                self._view_params["curr_row"],
                self._view_params["curr_col"],
                height,
                width,
            )

    def _post_input(self, height, width):
        """Render the pad after user input is entered.

        Args:
            height (int): Number of rows in the terminal.
            width (int): Number of columns in the terminal.

        Returns:
            None
        """
        pad_to_render = None
        if self._view_params["status_type"] == "normal":
            pad_to_render = self._all_passes_pad
        elif self._view_params["status_type"] in ["index", "pass"]:
            # using zero based indexing
            pass_id = self._view_params["pass_id"]
            if pass_id >= 0:
                self._view_params["status_type"] = "pass"
                if self._pass_pad_list[pass_id] is None:
                    self._build_pass_pad(pass_id)
                pad_to_render = self._pass_pad_list[pass_id]

        self._render_transpilation_pad(
            pad_to_render,
            self._view_params["curr_row"],
            self._view_params["curr_col"],
            height,
            width,
        )

    def display(self, stdscr):
        """Display the Qiskit Transpiler Debugger on the terminal.

        Args:
            stdscr (curses.window): The main window object provided by the curses library.

        Returns:
            None
        """
        key = 0

        # Clear and refresh the screen for a blank canvas
        stdscr.clear()
        stdscr.refresh()

        # initiate color
        self._init_color()

        # hide the cursor
        curses.curs_set(0)

        # reset view params
        self._reset_view_params()

        height, width = stdscr.getmaxyx()
        self._refresh_base_windows(True, height, width)

        # build the base transpiler pad using the transpilation sequence
        self._all_passes_table = self._get_all_passes_table()
        self._all_passes_pad = self._get_all_passes_pad()
        self._pass_pad_list = [None] * len(self.transpilation_sequence.steps)

        # build the individual pass pad list
        # done, via add_step
        assert len(self._pass_pad_list) > 0

        while key not in [ord("q"), ord("Q")]:
            height, width = stdscr.getmaxyx()

            # Check for clearing
            panel_initiated = self._view_params["last_height"] + self._view_params["last_width"] > 0
            panel_resized = (
                self._view_params["last_width"] != width
                or self._view_params["last_height"] != height
            )

            if panel_initiated and panel_resized:
                stdscr.clear()

            self._view_params["overview_change"] = False
            self._handle_keystroke(key)

            whstr = f"Width: {width}, Height: {height}"
            stdscr.addstr(0, 0, whstr)

            # refresh the screen and then the windows
            stdscr.noutrefresh()
            self._refresh_base_windows(panel_resized, height, width)

            # pre input rendering
            self._pre_input(height, width)

            # render the status bar , irrespective of width / height
            # and get the input (if any)
            self._status_bar = self._get_statusbar_win(
                height, width, self._view_params["status_type"]
            )
            self._status_bar.noutrefresh()

            # post input rendering
            self._post_input(height, width)

            self._view_params["last_width"] = width
            self._view_params["last_height"] = height

            curses.doupdate()

            # wait for the next input
            key = stdscr.getch()
