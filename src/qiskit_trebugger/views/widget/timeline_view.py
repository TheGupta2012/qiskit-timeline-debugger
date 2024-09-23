"""Main Timeline View for the Debugger
"""

import html
import math
import warnings
from collections import defaultdict
from datetime import datetime

import ipywidgets as widgets
from IPython.display import HTML
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.dagcircuit import DAGCircuit

from ...debugger_error import DebuggerError
from ...model.circuit_comparator import CircuitComparator
from ...model.circuit_stats import CircuitStats
from ...model.pass_type import PassType
from .button_with_value import ButtonWithValue
from .timeline_utils import (
    get_args_panel,
    get_spinner_html,
    get_styles,
    view_circuit,
    view_routing,
    view_timeline,
)


class TimelineView(widgets.VBox):
    """Class to implement the visual debugger.
    Inherits from the vertical box widget of
    ipywidgets module
    """

    def __init__(self, *args, **kwargs):
        self.layouts = {
            "timeline": {
                "border": "1px #eee",
                "padding": "2px",
                "height": "400px",
                "overflow": "auto",
                "width": "100%",
            },
            "tabular_data": {
                "padding": "5px",
                "grid_template_columns": "repeat(2, 50%)",
            },
        }

        style = widgets.HTML(get_styles())
        header = widgets.HTML(
            '<div class=" widget-gridbox" style="width: 100%; \
            grid-template-columns: auto 8%;"><div class=" title">\
            <h1>Qiskit Timeline Debugger</h1></div><div class="logo"></div></div>'
        )

        general_info_panel = widgets.GridBox(children=[], layout={"width": "100%"})
        general_info_panel.add_class("options")
        # summary panel
        summary_heading = widgets.HTML(
            "<h2 style = 'margin: 10px 20px 0 30px; \
                font-weight: bold;'> Transpilation overview</h2>"
        )
        summary_panel = widgets.VBox(
            [
                summary_heading,
                widgets.GridBox(
                    [],
                    layout={
                        "width": "100%",
                        "padding": "5px",
                        "grid_template_columns": "repeat(2, 50%)",
                    },
                ),
            ],
            layout={"width": "100%"},
        )

        # routing panel
        routing_heading = widgets.HTML(
            "<h2 style = 'margin: 10px 20px 0 30px; \
                font-weight: bold;'> Routing Overview</h2>"
        )

        routing_panel = widgets.VBox(
            [
                routing_heading,
                widgets.GridBox(
                    [],
                    layout={
                        "width": "100%",
                        "padding": "0 0 0 15px ",
                        "grid_template_columns": "repeat(2, 50%)",
                    },
                ),
            ],
            layout={
                "width": "100%",
            },
        )

        # timeline panel
        timeline_sched_heading = widgets.HTML(
            "<h2 style = 'margin: 10px 20px 0 30px; \
                font-weight: bold;'> Timeline Drawer</h2>"
        )
        timeline_sched_panel = widgets.VBox(
            [
                timeline_sched_heading,
                widgets.VBox(
                    [],
                    layout={
                        "width": "100%",
                        "padding": "5px",
                    },
                ),
            ],
            layout={"width": "100%"},
        )

        # params panel
        param_button = widgets.Button(
            description="Params set for Transpiler",
            icon="caret-right",
            tooltip="Params for transpilation",
            layout={"width": "auto"},
        )
        # callback to add the box
        param_button.add_class("toggle-button")
        param_button.on_click(self._add_args)

        params_panel = widgets.VBox([param_button], layout={"margin": "0 1% 0 1%"})

        self.timeline_panel = widgets.VBox([], layout={"width": "100%"})
        timeline_wpr = widgets.Box(
            [self.timeline_panel], layout=self.layouts["timeline"]
        )

        stats_title = widgets.Label("Circuit Stats")
        stats_title.add_class("stats-title")

        self.stats_labels = [
            widgets.Label("1q ops"),
            widgets.Label(""),
            widgets.Label("2q ops"),
            widgets.Label(""),
            widgets.Label("3+q ops"),
            widgets.Label(""),
            widgets.Label("Depth"),
            widgets.Label(""),
            widgets.Label("Size"),
            widgets.Label(""),
            widgets.Label("Width"),
            widgets.Label(""),
        ]

        stats_panel = widgets.GridBox(
            self.stats_labels, layout=self.layouts["tabular_data"]
        )
        stats_panel.add_class("table")

        toggle_pass_button = widgets.Button(
            description="Transpiler Passes",
            icon="caret-right",
            tooltip="Transpiler Passes",
            layout={"width": "auto"},
        )
        toggle_pass_button.add_class("toggle-button")
        toggle_pass_button.on_click(self._load_passes)

        self.main_panel = widgets.HBox(
            children=[timeline_wpr], layout={"width": "100%"}
        )

        pass_panel = widgets.VBox([toggle_pass_button], layout={"margin": "0 1% 0 1%"})

        super().__init__(*args, **kwargs)
        self.children = (
            style,
            header,
            general_info_panel,
            params_panel,
            summary_panel,
            routing_panel,
            timeline_sched_panel,
            pass_panel,
        )
        self.layout = {"width": "100%"}
        self.add_class("tp-widget")

        self.panels = {
            "general_info": general_info_panel,
            "summary": summary_panel,
            "routing": routing_panel,
            "timeline": timeline_sched_panel,
            "params": params_panel,
            "pass": pass_panel,
            "debug_output": widgets.Output(),
        }

        self.kwargs_box = None

        self._transpilation_sequence = None

    @property
    def transpilation_sequence(self):
        """Returns the transpilation_sequence object"""
        return self._transpilation_sequence

    @transpilation_sequence.setter
    def transpilation_sequence(self, transpilation_sequence):
        self._transpilation_sequence = transpilation_sequence

        # Set general info:
        items = []
        general_info = transpilation_sequence.general_info
        for key, value in general_info.items():
            items.append(widgets.Label(key + ": " + str(value)))
        self.panels["general_info"].children = items
        self.panels["general_info"].layout = {
            "width": "100%",
            "grid_template_columns": "repeat(" + str(len(general_info)) + ", auto)",
        }

    def update_summary(self):
        """Update the summary panel after the transpilation
        populates the transpilation sequence
        """
        self.panels["summary"].children[1].add_class("summary-panel")
        self.panels["summary"].children[1].children = self._get_summary_panel()

    def _get_summary_panel(self):
        # get the total count of passes
        total_passes = {"T": 0, "A": 0}

        for step in self.transpilation_sequence.steps:
            if step.pass_type == PassType.TRANSFORMATION:
                total_passes["T"] += 1
            else:
                total_passes["A"] += 1

        transform_head = widgets.HTML(
            r"""<p class = 'transform-label'>
                <b> Transformation Passes  </b></p>
                <p class = 'label-text'>
                """
            + str(total_passes["T"])
            + "</p>"
        )

        analyse_head = widgets.HTML(
            r"""<p class = 'analyse-label'>
                <b> Analysis Passes  </b></p>
                <p class = 'label-text'>
                """
            + str(total_passes["A"])
            + "</p>"
        )

        init_step = self.transpilation_sequence.steps[0]
        final_step = self.transpilation_sequence.steps[-1]

        # build overview
        overview = {"depths": {"init": 0, "final": 0}, "ops": {"init": 0, "final": 0}}

        # get the depths
        overview["depths"]["init"] = init_step.circuit_stats.depth
        overview["depths"]["final"] = final_step.circuit_stats.depth

        # get the op counts
        overview["ops"]["init"] = (
            init_step.circuit_stats.ops_1q
            + init_step.circuit_stats.ops_2q
            + init_step.circuit_stats.ops_3q
        )

        overview["ops"]["final"] = (
            final_step.circuit_stats.ops_1q
            + final_step.circuit_stats.ops_2q
            + final_step.circuit_stats.ops_3q
        )

        init_depth = widgets.HTML(
            r"<p class = 'label-purple-back'>"
            + "  Initial depth  </p> <p class = 'label-text'>"
            + str(overview["depths"]["init"])
            + "</p>"
        )

        final_depth = widgets.HTML(
            r"<p class = 'label-purple-back'>"
            + "  Final depth  </p> <p class = 'label-text'>"
            + str(overview["depths"]["final"])
            + "</p>"
        )

        init_ops = widgets.HTML(
            r"<p class = 'label-purple-back'>"
            + "  Initial Op count </p> <p class = 'label-text'>"
            + str(overview["ops"]["init"])
            + "</p>"
        )

        final_ops = widgets.HTML(
            r"<p class = 'label-purple-back'>"
            + "  Final Op count </p> <p class = 'label-text'>"
            + str(overview["ops"]["final"])
            + "</p>"
        )

        overview_children = [
            transform_head,
            analyse_head,
            init_depth,
            final_depth,
            init_ops,
            final_ops,
        ]

        return overview_children

    def update_routing(self, circ, backend, show_routing):
        """Update the routing information after the transpilation"""
        self.panels["routing"].children[1].add_class("routing-panel")
        self.panels["routing"].children[1].children = self._get_routing_panel(
            circ, backend, show_routing
        )

    def _get_routing_panel(self, final_circuit, backend, show_routing):
        # get two views of the routing
        if show_routing:
            try:
                virtual_head = widgets.HTML(
                    r"""<p class = 'label-purple-back'>
                        Virtual Mapping  </p>
                        """
                )
                physical_head = widgets.HTML(
                    r"""<p class = 'label-purple-back'>
                        Physical Mapping  </p>
                    """
                )
                layout = {
                    "width": "100%",
                    "height": "100%",
                    "margin": "0 0 0 1%",
                    "padding": "5px 0px 2px 15px",
                }
                virtual_routing = widgets.Output(layout=layout)
                virtual_routing.append_display_data(
                    HTML(view_routing(final_circuit, backend, "virtual"))
                )
                physical_routing = widgets.Output(layout=layout)
                physical_routing.append_display_data(
                    HTML(view_routing(final_circuit, backend, "physical"))
                )

                return [
                    virtual_head,
                    physical_head,
                    virtual_routing,
                    physical_routing,
                ]
            except Exception as ex:
                raise DebuggerError(
                    "Error plotting coupling map for backend. Ensure that graphviz is installed."
                    "You can install it using this reference - https://graphviz.org/download/"
                ) from ex
        else:
            return [
                widgets.HTML("<p class='label-text-2'> Coupling map not displayed </p>")
            ]

    def update_timeline(self, circ, schedule_type):
        """Update the timeline drawer information after the transpilation"""
        self.panels["timeline"].children[1].add_class("timeline-panel")
        self.panels["timeline"].children[1].children = self._get_timeline_panel(
            circ, schedule_type
        )

    def _get_timeline_panel(self, final_circuit, schedule_type):
        layout = {
            "width": "100%",
            "height": "100%",
            "margin": "0 0 0 1%",
            "padding": "5px 0px 2px 15px",
        }
        timeline_widget = None
        if schedule_type is None:
            timeline_widget = widgets.HTML(
                "<p class='label-text-2'> No scheduling method was set </p>",
            )
        else:
            timeline_widget = widgets.Output()
            timeline_widget.layout = layout
            timeline_widget.append_display_data(HTML(view_timeline(final_circuit)))

        return [timeline_widget]

    def _add_args(self, btn):
        # here, if the button has been clicked
        # change the caret and add the child
        param_children = list(self.panels["params"].children)

        if len(param_children) == 1:
            param_children.append(self.kwargs_box)
            btn.icon = "caret-down"

        else:
            del param_children[-1]
            btn.icon = "caret-right"

        self.panels["params"].children = param_children

    def update_params(self, **kwargs):
        """Updates the parameters of the transpilation in
        debugger
        """
        self.kwargs_box = get_args_panel(**kwargs)

    def _load_passes(self, btn):
        pass_children = list(self.panels["pass"].children)

        if len(pass_children) == 1:
            pass_children.append(self.main_panel)
            btn.icon = "caret-down"

        else:
            del pass_children[-1]
            btn.icon = "caret-right"

        self.panels["pass"].children = pass_children

    def add_step(self, step):
        """Add transpilation step into the widget

        Args:
            step (TranspilationStep): One pass of the transpiler
                                      modelled as a transpilation
                                      step"""
        step_items = []

        _item = ButtonWithValue(
            value=str(step.index),
            description="",
            icon="caret-right",
            tooltip=step.pass_type.value + " Pass",
            layout={"width": "11px"},
        )
        _item.on_click(self.on_pass)
        step_items.append(widgets.Box([_item]))

        _item = widgets.HTML("<div>" + str(step.index) + " | " + step.name + "</div>")
        _item.add_class(step.pass_type.value.lower())
        step_items.append(_item)

        if step.duration > 0:
            duration_font_size = 10
            duration_font_size = 10 + round(math.log10(step.duration))
            _item = widgets.Label(str(round(step.duration, 1)) + " ms")
            _item.add_class("fs" + str(duration_font_size))
        else:
            _item = widgets.Label("")
        step_items.append(_item)

        # circuit stats:
        if step.index == 0:
            prev_stats = CircuitStats()
        else:
            prev_stats = self.transpilation_sequence.steps[step.index - 1].circuit_stats

        _item = widgets.HTML(
            '<span class="stat-name">Depth </span><span class="stat-value">'
            + str(step.circuit_stats.depth)
            + "</span>"
        )
        if prev_stats.depth != step.circuit_stats.depth:
            _item.add_class("highlight")
        step_items.append(_item)

        _item = widgets.HTML(
            '<span class="stat-name">Size </span><span class="stat-value">'
            + str(step.circuit_stats.size)
            + "</span>"
        )
        if prev_stats.size != step.circuit_stats.size:
            _item.add_class("highlight")
        step_items.append(_item)

        _item = widgets.HTML(
            '<span class="stat-name">Width </span><span class="stat-value">'
            + str(step.circuit_stats.width)
            + "</span>"
        )
        if prev_stats.width != step.circuit_stats.width:
            _item.add_class("highlight")
        step_items.append(_item)

        _item = widgets.HTML(
            '<span class="stat-name">1Q ops </span><span class="stat-value">'
            + str(step.circuit_stats.ops_1q)
            + "</span>"
        )
        if prev_stats.ops_1q != step.circuit_stats.ops_1q:
            _item.add_class("highlight")
        step_items.append(_item)

        _item = widgets.HTML(
            '<span class="stat-name">2Q ops </span><span class="stat-value">'
            + str(step.circuit_stats.ops_2q)
            + "</span>"
        )
        if prev_stats.ops_2q != step.circuit_stats.ops_2q:
            _item.add_class("highlight")
        step_items.append(_item)

        item_wpr = widgets.GridBox(
            step_items,
            layout={
                "width": "100%",
                "min_height": "50px",
            },
        )
        item_wpr.add_class("transpilation-step")

        details_wpr = widgets.Box(layout={"width": "100%"})
        details_wpr.add_class("step-details")
        details_wpr.add_class("step-details-hide")

        self.timeline_panel.children = self.timeline_panel.children + (
            item_wpr,
            details_wpr,
        )

    def show_details(self, step_index, title, content):
        """Show the details of the transpilation step

        Args:
            step_index (int): Index of the transpilation step
            title (str): Title of the details
            content (str): Content of the details

        Returns:
            None
        """
        details_panel = self.timeline_panel.children[2 * step_index + 1]
        out = widgets.Output(layout={"width": "100%"})
        details_panel.children = (out,)

        if "step-details-hide" in details_panel._dom_classes:
            details_panel.remove_class("step-details-hide")

        html_str = f"""
        <div class="content-wpr">
            <div class="content">{content}</div>
        </div>
        """
        out.append_display_data(HTML(html_str))

    def on_pass(self, btn):
        """Render the pass view on the clicking of the button
        on the left of the pass panel
        Args:
            btn (ButtonWithValue): Button which contains the
                                   pass index"""
        step_index = int(btn.value)
        step = self.transpilation_sequence.steps[step_index]

        # Toggle detailed view:
        details_panel = self.timeline_panel.children[2 * step_index + 1]
        if "step-details-hide" not in details_panel._dom_classes:
            details_panel.add_class("step-details-hide")
            btn.icon = "caret-right"
        else:
            details_panel.remove_class("step-details-hide")
            btn.icon = "caret-down"

        if len(details_panel.children) == 0:
            # First time to expand this panel
            tab_titles = ["Circuit", "Property Set", "Logs", "Help"]
            children = [
                widgets.VBox(layout={"width": "100%"}),
                widgets.HBox(
                    children=[
                        widgets.GridBox(
                            [],
                            layout={
                                "width": "50%",
                                "padding": "5px",
                                "grid_template_columns": "repeat(2, 50%)",
                            },
                        ),
                        widgets.Output(layout={"width": "50%"}),
                    ],
                    layout={"width": "100%"},
                ),
                widgets.Output(layout={"width": "100%"}),
                widgets.Output(layout={"width": "100%"}),
            ]

            tab = widgets.Tab(model_id=str(step_index), layout={"width": "100%"})
            tab.children = children
            for idx, name in enumerate(tab_titles):
                tab.set_title(idx, name)

            details_panel.children = (tab,)
            dag = self._get_step_dag(step)

            self._load_img_view(dag, tab, step_index)

            tab.observe(self.on_tab_clicked)

            children[1].children[0].add_class("property-set")
            children[1].children[1].add_class("property-items")

            if len(self._get_step_property_set(step)) == 0:
                tab.add_class("no-props")
            if len(step.logs) == 0:
                tab.add_class("no-logs")

    def _load_img_view(self, dag, tab, step_index):
        if isinstance(dag, DAGCircuit):
            img_wpr = widgets.Output(layout={"width": "100%"})
            img_wpr.append_display_data(HTML(get_spinner_html()))

            circ = dag_to_circuit(dag)
            img_html = view_circuit(circ, "after_pass_" + str(step_index))
            img_wpr.outputs = []
            img_wpr.append_display_data(HTML(img_html))

            diff_chk = widgets.Checkbox(
                model_id="step:" + str(step_index),
                value=False,
                description="Highlight diff",
                indent=False,
            )
            diff_chk.observe(self.on_diff)
            tab.children[0].children = (diff_chk, img_wpr)

        else:
            message = widgets.Label(
                value="Displaying circuits with depth larger than 300 is not supported!"
            )
            message.add_class("message")
            tab.children[0].children = (message,)

    def on_tab_clicked(self, change):
        """Callback to update the information on the debugger view when a
           tab is clicked from properties, logs or docs

        Args:
            change (dict): Dict describing the state of the
                           widget
        """
        if change["type"] == "change" and change["name"] == "selected_index":
            tabs = change.owner
            step_index = int(tabs.model_id)
            # get the transpiler pass which is displayed
            step = self.transpilation_sequence.steps[step_index]

            if change["new"] == 1:
                properties_panel = tabs.children[1].children[0]

                # If content is already rendered, do nothing:
                if (
                    isinstance(tabs.children[1].children[0], widgets.Label)
                    or len(properties_panel.children) > 0
                ):
                    return

                _property_set = self._get_step_property_set(step)
                if len(_property_set) > 0:
                    properties_panel.add_class("table")
                    properties_panel.layout = {
                        "width": "50%",
                        "padding": "5px",
                        "grid_template_columns": "repeat(2, 50%)",
                        "height": str(33 * len(_property_set)) + "px",
                    }

                    for prop_name in _property_set:
                        property_ = _property_set[prop_name]
                        prop_widget = widgets.Label(value=property_.name)
                        if property_.prop_type not in (int, float, bool, str):
                            txt = (
                                "(dict)"
                                if isinstance(property_.value, defaultdict)
                                else "(" + property_.prop_type.__name__ + ")"
                            )
                            prop_label = widgets.Label(txt, layout={"width": "80%"})
                            prop_button = ButtonWithValue(
                                value=None, description="...", layout={"width": "20%"}
                            )
                            prop_button.on_click(self.on_property)
                            prop_box = widgets.HBox(
                                [prop_label, prop_button], layout={"width": "100%"}
                            )
                        else:
                            prop_box = widgets.Label(value=str(property_.value))

                        if step.property_set_index == step.index:
                            if property_.state != "updated":
                                prop_widget.add_class(property_.state)
                            prop_box.add_class(property_.state)

                        index = len(properties_panel.children)
                        properties_panel.children = properties_panel.children + (
                            prop_widget,
                            prop_box,
                        )

                        if property_.prop_type not in (int, float, bool, str):
                            properties_panel.children[index + 1].children[1].value = (
                                str(step.index) + "," + property_.name
                            )
                        else:
                            properties_panel.children[index + 1].value = str(
                                property_.value
                            )

                    prop_list = list(properties_panel.children)
                    for p_id in range(int(len(prop_list) / 2)):
                        if (
                            properties_panel.children[2 * p_id].value
                            not in _property_set
                        ):
                            properties_panel.children[2 * p_id].add_class("not-exist")
                            properties_panel.children[2 * p_id + 1].add_class(
                                "not-exist"
                            )
                        else:
                            properties_panel.children[2 * p_id].remove_class(
                                "not-exist"
                            )
                            properties_panel.children[2 * p_id + 1].remove_class(
                                "not-exist"
                            )
                else:
                    message = widgets.Label(value="Property set is empty!")
                    message.add_class("message")
                    tabs.children[1].children = (message,)

            elif change["new"] == 2:
                # for the Logs tab of the debugger

                # If content is already rendered, do nothing:
                if len(tabs.children[2].outputs) > 0:
                    return

                logs = step.logs
                if len(logs) > 0:
                    html_str = '<div class="logs-wpr">'
                    for entry in logs:
                        html_str = (
                            html_str
                            + "<pre class='date'>{0}</pre>\
                                <pre class='level {1}'>[{1}]\
                                </pre><pre class='log-entry {1}'>\
                                {2}</pre>".format(
                                datetime.fromtimestamp(entry.time).strftime(
                                    "%H:%M:%S.%f"
                                )[:-3],
                                entry.levelname,
                                entry.msg % entry.args,
                            )
                        )
                    html_str = html_str + "</div>"
                    tabs.children[2].append_display_data(HTML(html_str))
                else:
                    html_str = '<div class="message">This pass does not \
                        write any log messages!</div>'
                    tabs.children[2].append_display_data(HTML(html_str))

            elif change["new"] == 3:
                # this is the docs tab

                # If content is already rendered, do nothing:
                if len(tabs.children[3].outputs) > 0:
                    return

                html_str = '<pre class="help">' + step.docs + "</pre>"
                html_str = (
                    html_str
                    + '<div class="help-header"><span style="color: #e83e8c;">'
                    + step.name
                    + '</span>.run(<span style="color: #0072c3;">dag</span>)</div>'
                )
                html_str = (
                    html_str + '<pre class="help">' + step.run_method_docs + "</pre>"
                )
                tabs.children[3].append_display_data(HTML(html_str))

    def on_diff(self, change):
        """Callback to handle the toggling of circuit diff in the debugger

        Args:
            change (dict): Dict containing the current state of the
                           widget associated with the callback
        """
        if (
            change["type"] == "change"
            and isinstance(change["new"], dict)
            and "value" in change["new"]
        ):
            chk = change.owner
            _, step_index_str = chk.model_id.split(":")
            step_index = int(step_index_str)

            details_panel = self.timeline_panel.children[2 * int(step_index) + 1]
            img_wpr = details_panel.children[0].children[0].children[1]
            img_wpr.outputs = []
            img_wpr.append_display_data(
                HTML(get_spinner_html())
            )  # to get the loader gif

            if change["new"]["value"]:
                if step_index > 0:
                    prev_dag = self._get_step_dag(
                        self.transpilation_sequence.steps[step_index - 1]
                    )
                    prev_circ = dag_to_circuit(prev_dag)
                else:
                    prev_circ = None

                curr_dag = self._get_step_dag(
                    self.transpilation_sequence.steps[step_index]
                )
                curr_circ = dag_to_circuit(curr_dag)
                fully_changed, disp_circ = CircuitComparator.compare(
                    prev_circ, curr_circ
                )

                if fully_changed:
                    chk.description = "Circuit changed fully"
                    chk.disabled = True

                suffix = "diff_" + str(step_index)
            else:
                if not chk.disabled:
                    dag = self._get_step_dag(
                        self.transpilation_sequence.steps[step_index]
                    )
                    disp_circ = dag_to_circuit(dag)
                    suffix = "after_pass_" + str(step_index)

            # here, qasm and qpy need the without diff circuits
            img_html = view_circuit(disp_circ, suffix)
            img_wpr.outputs = []
            img_wpr.append_display_data(HTML(img_html))

    def on_property(self, btn):
        """Callback to handle the toggling of properties in the debugger

        Args:
            btn (ButtonWithValue): Button associated with the callbacks
        """
        warnings.filterwarnings(
            "ignore",
            message="Back-references to from Bit instances to \
            their containing Registers have been deprecated. \
            Instead, inspect Registers to find their contained Bits.",
        )

        step_index, property_name = btn.value.split(",")

        details_panel = self.timeline_panel.children[2 * int(step_index) + 1]
        prop_details_panel = details_panel.children[0].children[1].children[1]

        step = self.transpilation_sequence.steps[int(step_index)]
        property_set = self._get_step_property_set(step)
        property_ = property_set[property_name]

        html_str = '<table style="width: 100%">'
        html_str = (
            html_str
            + '<thead><tr><th colspan="'
            + ("2" if isinstance(property_.value, defaultdict) else "1")
            + '">'
            + property_name
            + "</th></tr></thead>"
        )
        if property_name == "block_list":
            for val in property_.value:
                v_arr = []
                for node in val:
                    qargs = ", ".join(
                        [
                            qarg.register.name
                            + "<small>["
                            + str(qarg.index)
                            + "]</small>"
                            for qarg in node.qargs
                        ]
                    )
                    v_arr.append(
                        "<strong>" + node.name + "</strong>" + "(" + qargs + ")"
                    )
                html_str = html_str + "<tr><td>" + " - ".join(v_arr) + "</td></tr>"
        elif property_name == "commutation_set":
            for key, val in property_.value.items():
                key_str = ""
                if isinstance(key, tuple):
                    qargs = ", ".join(
                        [
                            qarg.register.name
                            + "<small>["
                            + str(qarg.index)
                            + "]</small>"
                            for qarg in key[0].qargs
                        ]
                    )
                    key_str = (
                        "(<strong>"
                        + (key[0].name if key[0].name is not None else "")
                        + "</strong>("
                        + qargs
                        + "), "
                    )
                    key_str = (
                        key_str
                        + key[1].register.name
                        + "<small>["
                        + str(key[1].index)
                        + "]</small>"
                        + ")"
                    )
                else:
                    key_str = (
                        key.register.name + "<small>[" + str(key.index) + "]</small>"
                    )

                value_str = ""
                if isinstance(val, list):
                    value_str = value_str + "["
                    for nodes in val:
                        if isinstance(nodes, list):
                            nodes_arr = []
                            for node in nodes:
                                if node.type == "op":
                                    qargs = ", ".join(
                                        [
                                            qarg.register.name
                                            + "<small>["
                                            + str(qarg.index)
                                            + "]</small>"
                                            for qarg in node.qargs
                                        ]
                                    )
                                    node_str = (
                                        "<strong>"
                                        + (node.name if node.name is not None else "")
                                        + "</strong>"
                                        + "("
                                        + qargs
                                        + ")"
                                    )
                                else:
                                    node_str = (
                                        node.type.upper()
                                        + "(wire="
                                        + node.wire.register.name
                                        + "<small>["
                                        + str(node.wire.index)
                                        + "]</small>)"
                                    )

                                nodes_arr.append(node_str)

                            value_str = (
                                value_str + "[" + (", ".join(nodes_arr)) + "]<br>"
                            )
                    value_str = value_str + "]"

                html_str = (
                    html_str
                    + '<tr><td style="width:50%">'
                    + key_str
                    + "</td><td><pre>"
                    + value_str
                    + "</pre></td></tr>"
                )
        else:
            html_str = (
                html_str
                + "<tr><td><pre>"
                + html.escape(str(property_.value))
                + "</pre></td></tr>"
            )
        html_str = html_str + "</table>"

        prop_details_panel.outputs = []
        prop_details_panel.append_display_data(HTML(html_str))

    def _get_step_dag(self, step):
        if step.pass_type == PassType.TRANSFORMATION:
            return step.dag

        idx = step.index
        # Due to a bug in DAGCircuit.__eq__, we can not use ``step.dag != None``

        found_transform = False
        while (
            not isinstance(self.transpilation_sequence.steps[idx].dag, DAGCircuit)
            and idx > 0
        ):
            idx = idx - 1
            if idx >= 0:
                found_transform = (
                    self.transpilation_sequence.steps[idx].pass_type
                    == PassType.TRANSFORMATION
                )

        if found_transform is False:
            return circuit_to_dag(self.transpilation_sequence.original_circuit)

        return self.transpilation_sequence.steps[idx].dag

    def _get_step_property_set(self, step):
        if step.property_set_index is not None:
            return self.transpilation_sequence.steps[
                step.property_set_index
            ].property_set

        return {}
