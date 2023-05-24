import curses
import tabulate
from curses.textpad import Textbox

from ...model.pass_type import PassType


class CLIView:
    def __init__(self):
        # define different components
        self._title = None
        self._overview = None
        self._all_passes_pad = None
        self._individual_pad_list = None
        self._status_bar = None
        self._title_string = "Qiskit Transpiler Debugger"

        self._status_strings = {
            "normal": " STATUS BAR  | ↑↓ keys / mouse cursor: Scrolling | 'I': Index into a pass | 'Q': Exit",
            "index": " STATUS BAR  | Enter the index of the pass you want to view : ",
            "invalid": " STATUS BAR  | Invalid input entered. Press Enter to continue.",
            "out_of_bounds": " STATUS BAR  | Number entered is out of bounds. Please Enter to continue.",
            "pass": " STATUS BAR  | Arrow keys: Scrolling | 'N/P': Move to next/previous pass | 'I': Index into a pass | 'B': Back to all passes | 'Q': Exit",
        }
        # define status object
        self._reset_view_params()

        # add the transpilation sequence
        self.transpilation_sequence = None

    def _reset_view_params(self):
        self._view_params = {
            "curr_row": 0,
            "curr_col": 0,
            "last_width": 0,
            "last_height": 0,
            "pass_id": -1,
            "transpiler_start_row": 6,
            "transpiler_start_col": None,
            "status_type": "normal",
        }

    def _init_color(self):
        # Start colors in curses
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)
        self.CYAN_ON_BLACK = curses.color_pair(1)
        self.MAGENTA_ON_WHITE = curses.color_pair(2)
        self.BLACK_ON_CYAN = curses.color_pair(3)
        self.WHITE_ON_BLACK = curses.color_pair(4)

    def _get_center(self, width, string_len, divisor=2):
        return max(0, int(width // divisor - string_len // 2 - string_len % 2))

    def _handle_keystroke(self, key):
        if key == curses.KEY_UP:
            self._view_params["curr_row"] -= 1
            self._view_params["curr_row"] = max(self._view_params["curr_row"], 0)
        elif key == curses.KEY_LEFT:
            self._view_params["curr_col"] -= 1
            self._view_params["curr_col"] = max(self._view_params["curr_col"], 0)

        # to do

        # elif key == curses.KEY_DOWN:
        #     self._view_params["curr_row"] += 1
        #     if self._view_params["status_type"] == "normal":
        #         self._view_params["curr_row"] = min(
        #             self._view_params["curr_row"], len(self._pass_table) - 1
        #         )
        #     elif self._view_params["status_type"] in ["index", "pass"]:
        #         self._view_params["curr_row"] = min(
        #             # as we have 350 rows by default
        #             self._view_params["curr_row"],
        #             349,
        #         )

        # elif key == curses.KEY_RIGHT:
        #     curr_col += 1

        #     if status_type == "normal":
        #         curr_col = min(curr_col, len(pass_table[1]) - 1)
        #     elif status_type in ["index", "pass"]:
        #         curr_col = min(
        #             curr_col,
        #             curses.COLS - TRANSPILER_STEPS_DIMS["PASSES_START_COL"] - 1,
        #         )
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
        title_window.bkgd(self.MAGENTA_ON_WHITE)
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

        for prop in overview_stats:  # prop should have same name as in CircuitStats
            overview_stats[prop]["init"] = init_step_dict[prop]
            overview_stats[prop]["final"] = final_step_dict[prop]

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

    def _build_overview_win(self, cols):
        overview_rows = 26
        overview_cols = cols
        begin_row = 6
        overview_win = curses.newwin(overview_rows, overview_cols, begin_row, 0)

        total_passes = {"T": 0, "A": 0}
        for step in self.transpilation_sequence.steps:
            if step.pass_type == PassType.TRANSFORMATION:
                total_passes["T"] += 1
            else:
                total_passes["A"] += 1

        total_pass_str = f"Total Passes : {total_passes['A'] + total_passes['T']}"[
            : overview_cols - 1
        ]
        pass_categories_str = (
            f"Transformation : {total_passes['T']} | Analysis : {total_passes['A']}"[
                : overview_cols - 1
            ]
        )

        start_x = 5
        overview_win.addstr(
            5, start_x, "Pass Overview"[: overview_cols - 1], curses.A_BOLD
        )
        overview_win.addstr(6, start_x, total_pass_str)
        overview_win.addstr(7, start_x, pass_categories_str)

        # runtime
        runtime_str = (
            f"Runtime : {round(self.transpilation_sequence.total_runtime,2)} ms"[
                : overview_cols - 1
            ]
        )
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
            overview_win.addstr(
                row, start_x, stats_table[row - 12][: overview_cols - 1]
            )

        # for correct formatting of title
        max_line_length = len(stats_table[0])

        # add titles

        # stats header
        stats_str = "Circuit Statistics"[: overview_cols - 1]
        stats_head_offset = self._get_center(max_line_length, len(stats_str))
        overview_win.addstr(11, start_x + stats_head_offset, stats_str, curses.A_BOLD)

        # overview header
        overview_str = "TRANSPILATION OVERVIEW"[: overview_cols - 1]
        start_x_overview = start_x + self._get_center(
            max_line_length, len(overview_str)
        )
        overview_win.hline(0, start_x, "_", min(cols, max_line_length))
        overview_win.addstr(2, start_x_overview, overview_str, curses.A_BOLD)
        overview_win.hline(3, start_x, "_", min(cols, max_line_length))

        # update the dimensions
        self._view_params["transpiler_start_col"] = start_x + max_line_length + 5
        return overview_win

    def _get_pass_title(self, cols):
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
        except:
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

        Returns:
            curses.window : Statusbar window object
        """
        # normal        : normal status bar
        # index         : index status bar - user is entering the numbers (requires input to be shown to user)
        # invalid       : error status bar - user has entered an invalid character
        # out_of_bounds : out of bounds status bar - user has entered a number out of bounds
        # pass          : pass status bar - user has entered a valid number and is now viewing the pass details

        # NOTE : processing is done after the user presses enter.

        # This will only return a status bar window, TEXT processing is done within this function ONLY

        status_str = self._status_strings[status_type][: cols - 1]

        statusbar_window = curses.newwin(1, cols, rows - 1, 0)
        statusbar_window.bkgd(" ", self.BLACK_ON_CYAN)

        offset = 0
        statusbar_window.addstr(0, offset, status_str)
        offset += len(status_str)

        # now if index, enter a text box
        if status_type == "index":
            textbox = Textbox(statusbar_window)
            textbox.edit()
            str_value = (
                textbox.gather().split(":")[1].strip()
            )  # get the value of the entered text

            try:
                num = int(str_value)
                total_passes = len(self.transpilation_sequence.steps)
                if num >= total_passes or num < 0:
                    status_str = self._status_strings["out_of_bounds"]
                else:
                    status_str = self._status_strings["pass"]
                    self._view_params["pass_id"] = num
            except:
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

            self._overview = self._build_overview_win(width)
            self._overview.noutrefresh()

            pass_title_window = self._get_pass_title(width)
            if pass_title_window:
                pass_title_window.noutrefresh()

        # render the status bar , irrespective of width / height
        self._status_bar = self._get_statusbar_win(
            height, width, self._view_params["status_type"]
        )
        self._status_bar.noutrefresh()
        curses.doupdate()

    def add_step(self, step):
        # build the pass pad list step by step!! :)
        pass

    def display(self, stdscr):
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
        # to do

        # build the individual pass pad list
        # to do

        while key not in [ord("q"), ord("Q")]:
            # Initialization
            height, width = stdscr.getmaxyx()

            # Check for clearing
            panel_initiated = (
                self._view_params["last_height"] + self._view_params["last_width"] > 0
            )
            panel_resized = (
                self._view_params["last_width"] != width
                or self._view_params["last_height"] != height
            )
            if panel_initiated and panel_resized:
                stdscr.clear()

            # handle key strokes
            self._handle_keystroke(key)

            # render width and height
            whstr = "Width: {}, Height: {}".format(width, height)
            stdscr.addstr(0, 0, whstr, curses.color_pair(1))

            # refresh the screen and then the windows
            stdscr.refresh()

            self._refresh_base_windows(panel_resized, height, width)

            self._view_params["last_width"] = width
            self._view_params["last_height"] = height

            # to do : add the pass rendering

            # wait for the next input
            key = stdscr.getch()
