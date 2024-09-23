"""Utility functions to support the timeline view
"""

import base64
import os
from binascii import b2a_base64
from io import BytesIO

import ipywidgets as widgets
from qiskit import qpy as qpy_serialization
from qiskit.qasm3 import dumps as qasm3_dumps
from qiskit.visualization import plot_circuit_layout, timeline_drawer


def get_args_panel(**kwargs):
    """Returns kwarg panel for the debugger

    Returns:
        widgets.HBox: Horizontal Box containing the
                      arg panel
    """
    # make two boxes for each key and values
    key_box = {}
    val_box = {}

    box_kwargs = {
        "width": "50%",
        "display": "flex",
        "align_items": "stretch",
        "flex_flow": "column",
    }
    for i in range(2):
        key_box[i] = widgets.VBox(layout=box_kwargs)
        val_box[i] = widgets.VBox(layout=box_kwargs)

    # make children dicts
    key_children = {0: [], 1: []}
    value_children = {0: [], 1: []}

    # counter
    index = 0

    for i, (key, val) in enumerate(kwargs.items()):
        if val is None:
            continue

        # make key and value labels
        key_label = widgets.HTML(r"<p class = 'params-key'><b> " + key + "</b></p>")

        value = val
        value_label = widgets.HTML(r"<p class = 'params-value'>" + str(value) + "</p>")

        # add to the list
        key_children[index].append(key_label)
        value_children[index].append(value_label)

        # flip box id
        index = 0 if i < len(kwargs.items()) // 2 else 1

    # construct the inner vertical boxes
    for i in range(2):
        key_box[i].children = key_children[i]
        val_box[i].children = value_children[i]

    # construct HBoxes
    args_boxes = [
        widgets.HBox([key_box[0], val_box[0]], layout={"width": "50%"}),
        widgets.HBox([key_box[1], val_box[1]], layout={"width": "50%"}),
    ]

    # construct final HBox
    return widgets.HBox(args_boxes, layout={"margin": "10px 0 0 15px"})


def _get_img_html(fig):
    """Returns the html string for the image

    Args:
        fig (matplotlib.figure.Figure): The figure to convert to html

    Returns:
        str: HTML string with img data to be
             rendered into the debugger
    """
    img_bio = BytesIO()
    fig.savefig(img_bio, format="png", bbox_inches="tight")
    fig.clf()
    img_data = b2a_base64(img_bio.getvalue()).decode()
    img_html = f"""
        <div class="circuit-plot-wpr">
            <img src="data:image/png;base64,{img_data}&#10;">
        </div>
        """
    return img_html


def view_routing(circuit, backend, route_type):
    """Displays the routing of the circuit

    Args:
        circuit (QuantumCircuit): The circuit to route
        backend (IBMQBackend): The backend to route on
        route_type (str): The routing type to use

    Returns:
        str: HTML string with img data to be
             rendered into the debugger
    """
    fig = plot_circuit_layout(circuit, backend, route_type)
    return _get_img_html(fig)


def view_timeline(circuit):
    """Displays the timeline of the circuit

    Args:
        circuit (QuantumCircuit): The circuit for timeline view

    Returns:
        str: HTML string with img data to be
             rendered into the debugger
    """
    fig = timeline_drawer(circuit)
    return _get_img_html(fig)


def view_circuit(disp_circuit, suffix):
    """Displays the circuit with diff for the debuuger

    Args:
        disp_circuit : The circuit to display
        suffix (str) : The name to be added to pass

     Returns:
         str : HTML string with img data to be
               rendered into the debugger
    """
    if "diff" in suffix:
        # means checkbox has been chosen for diff
        img_style = {"gatefacecolor": "orange", "gatetextcolor": "black"}
    else:
        img_style = None

    fig = disp_circuit.draw(
        "mpl",
        idle_wires=False,
        with_layout=False,
        scale=0.9,
        fold=20,
        style=img_style,
    )

    img_bio = BytesIO()
    fig.savefig(img_bio, format="png", bbox_inches="tight")
    fig.clf()
    img_data = b2a_base64(img_bio.getvalue()).decode()

    qpy_bio = BytesIO()
    qpy_serialization.dump(disp_circuit, qpy_bio)
    qpy_data = b2a_base64(qpy_bio.getvalue()).decode()

    # qasm couldn't handle the circuit changed names
    # for instr in disp_circuit.data:
    #     instr[0].name = instr[0].name.strip()

    qasm_str = qasm3_dumps(disp_circuit)
    qasm_bio = BytesIO(bytes(qasm_str, "ascii"))
    qasm_data = b2a_base64(qasm_bio.getvalue()).decode()

    img_html = f"""
        <div class="circuit-plot-wpr">
            <img src="data:image/png;base64,{img_data}&#10;">
        </div>
        <div class="circuit-export-wpr">
            Save:
            <a download="circuit_{suffix}.png" href="data:image/png;base64,{img_data}" download>
                <i class="fa fa-download"></i> <span>PNG</span>
            </a>
            <a download="circuit_{suffix}.qpy" href="data:application/octet-stream;base64,{qpy_data}" download>
                <i class="fa fa-download"></i> <span>QPY</span>
            </a>
            <a download="circuit_{suffix}.qasm" href="data:application/octet-stream;base64,{qasm_data}" download>
                <i class="fa fa-download"></i> <span>QASM</span>
            </a>
        </div>
        """
    return img_html


def get_spinner_html():
    """Return the spinner html string"""
    return '<div class="lds-spinner"><div></div><div></div><div>\
            </div><div></div><div></div><div></div><div></div><div>\
            </div><div></div><div></div><div></div><div></div></div>'


def get_styles():
    """Return the style for the debugger"""
    # Construct the path to the image file
    script_dir = os.path.dirname(__file__)
    image_path = os.path.join(script_dir, "resources", "qiskit-logo.png")
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        final_style = (
            """
            <style>
            .title h1 { font-size: 45px; font-weight: bold; 
                        text-align: center; padding: 10px 10px 10px 10px; }
            .logo { margin: 0 15px; background-position: center; background-repeat: no-repeat;
                    background-size: contain; background-image: url('data:image/png;base64,"""
            + encoded_image
            + """');} 
            .step-details { min-height: 350px; background: #eee; }
            .step-details-hide { display: none !important; }

            .options { border-top: 1px solid #eee; }
            .options > div { font-size : 0.7 em; text-align: center; padding-left: 15px; 
                             font-family: 'Roboto Mono', monospace; background: #eee; }

            .tp-widget { border:1px solid #aaa; min-width: 300px; }
            .p-TabPanel-tabContents { padding: 5px !important; }
            .p-Collapse-header { padding: 1px 5px; background: #eee; }
            .p-Collapse-open > .p-Collapse-header { background: #ddd; }
            .p-Collapse-contents { padding-top: 0; padding-left: 0; padding-bottom: 0; 
                                   padding-right: 0; height: 220px; background: #f5f5f5; }
            .p-Collapse-contents button {
                width: 20%;
                background: #fff;
                text-align: center;
                padding: 0;
                font-weight: bold; }


            div.output_scroll { box-shadow: none }

            .widget-gridbox.table { background: #f5f5f5; }
            .widget-gridbox.table .widget-label {
                background-color: #fff;
                padding: 0 3px;
                font-family: 'Open Sans', monospace;
                font-size: 14px;
            }

            .exist { font-weight: bold; }
            .not-exist { display: none; }

            .stats-title {
                background: #eee;
                margin: 0;
                text-align: center;
                font-size: 15px;
                font-weight: bold;
                font-family: 'Roboto Mono', monospace; }

            .widget-label.new, .widget-hbox.new .widget-label { font-weight: bold; color: #4b7bec; }
            .widget-label.updated, .widget-hbox.updated .widget-label { font-weight: bold; color: #e74c3c; }

            .transpilation-step {
                background: #fff;
                padding-top: 5px;
                border-bottom: 1px solid #ddd;
                grid-template-columns: 35px auto 70px 70px 70px 70px 70px 70px;
            }
            .transpilation-step:hover { background: #eee; }
            .transpilation-step button { background: #fff; }
            .transpilation-step .transformation {
                                color: cornsilk;
                                font-family : 'Lato';
                                text-align: left;
                                padding: 3px 3px 0px 15px;
                                background-color: rgba(0, 67, 206, 0.8);
                                margin-right : 10%;
            }
            .transpilation-step .analysis {
                            color: cornsilk;
                            padding: 3px 3px 0px 15px;
                            font-family : 'Lato';
                            text-align: left;
                            background-color: rgba(180, 77, 224, 0.8);
                            margin-right: 10%;
            }

            .transpilation-step div.fs10 { font-size: 10px; }
            .transpilation-step div.fs11 { font-size: 11px; }
            .transpilation-step div.fs12 { font-size: 12px; }
            .transpilation-step div.fs13 { font-size: 13px; }
            .transpilation-step div.fs14 { font-size: 14px; }
            .transpilation-step div.fs15 { font-size: 15px; }
            .transpilation-step > :nth-child(1) button { width: 11px; font-size: 20px; background: transparent; outline: 0 !important; border: none !important; }
            .transpilation-step > :nth-child(1) button:hover { border: none !important; outline: none !important; box-shadow: none !important; }
            .transpilation-step > :nth-child(1) button:focus { border: none !important; outline: none !important; box-shadow: none !important; }

            .transpilation-step.active > :nth-child(2) { font-weight: bold; }

            .transpilation-step > :nth-child(2) {
                font-family: 'Roboto Mono', monospace;
                font-size: 16px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .transpilation-step > :nth-child(3) { font-family: 'Roboto Mono', monospace; font-size: 10px; color: #900; text-align: right; }
            .transpilation-step > :nth-child(4) { font-family: 'Roboto Mono', monospace; text-align: center; }
            .transpilation-step > :nth-child(5) { font-family: 'Roboto Mono', monospace; text-align: center; }
            .transpilation-step > :nth-child(6) { font-family: 'Roboto Mono', monospace; text-align: center; }
            .transpilation-step > :nth-child(7) { font-family: 'Roboto Mono', monospace; text-align: center; }
            .transpilation-step > :nth-child(8) { font-family: 'Roboto Mono', monospace; text-align: center; }

            .stat-name { font-size: 10px; color: #aaa; }
            .stat-value { font-size: 12px; color: #000; }
            .highlight .stat-value { font-weight: bold; color: #e74c3c; }

            .logs-wpr { display: grid; grid-template-columns: 70px 60px auto; }
            .logs-wpr pre.date { font-size: 10px; }
            .logs-wpr pre.level { font-size: 10px; text-align: right; padding-right: 5px; }
            .logs-wpr pre.log-entry { font-size: 12px; }
            .logs-wpr pre.DEBUG { color: #000000; }
            .logs-wpr pre.INFO { color: #1c84a2; }
            .logs-wpr pre.WARNING { color: #ed7723; }
            .logs-wpr pre.ERROR { color: #d64e4a; }
            .logs-wpr pre.CRITICAL { color: white; background: #d64e4a; }

            div.output_area pre.help { font-family: Helvetica,Arial,sans-serif; font-size: 13px;
                border: 1px solid #ccc; padding: 10px;}
            div.help-header {
                font-family: 'Roboto Mono', monospace;
                font-size: 12px;
                border: 1px solid #ccc;
                border-bottom: none;
                margin-top: 4px;
                padding: 5px 10px;
                font-weight: bold;
                background: #f5f5f5;
            }
            .toggle-button{
                padding: 5px 25px 10px 10px;
                font-size : 1.1em;
                height : 5%;
                text-align: left;
                background: #fff;
                transition: 0.5s;
                border: none !important;
            }
            .toggle-button:hover{
                background: #eee;
                border: none;
                transition: 1s;
            }
            .params-key{
                margin: 2% 1% 1% 4%;
                padding: 5px 20px 5px 20px;
                font-size: 1em;
                color: cornsilk;
                background: rgba(15,23,229,0.7);
            }

            .params-value{
                margin: 1% 1% 1% 1%;
                padding: 5px 20px 5px 20px;
                border-left : 2px solid black;
                font-size: 1.1em;
            }

            .transform-label {
                margin-left : 5%;
                color: cornsilk;
                padding: 10px 15px 10px 15px;
                font-size: 1.3em;
                background-color: rgba(0, 67, 206, 0.8);
            }

            .analyse-label {
                margin-left : 5%;
                padding: 10px 15px 10px 15px;
                color: cornsilk;
                font-size: 1.3em;
                background-color: rgba(180, 77, 224, 0.8);
            }

            .label-text{
                padding: 2px 2px 2px 2px; margin-left:10%; font-size: 1.1em;
            }
            
            .label-text-2{
                padding: 2px 2px 2px 2px; margin-left:2%; font-size: 1.1em;
            }

            .label-purple-back{
                margin-left : 5%;
                padding: 5px 0px 2px 15px;
                font-size: 1.2em;
                color : #444444;
                background-color: rgba(245,174,230,0.4);
            }


            .content-wpr {
                overflow:hidden;
            }

            .content { overflow-y: auto; height: 325px; margin: 0; padding: 0; }
            .p-TabPanel-tabContents td { text-align: left; font-family: 'Roboto Mono', monospace; }
            .p-TabPanel-tabContents th { text-align: center; font-family: 'Roboto Mono', monospace; font-size: 14px; }

            .circuit-plot-wpr { height: 225px; overflow: auto; border: 1px solid #aaa; }
            .circuit-plot-wpr img { max-width: none; }
            .circuit-export-wpr a {
                display: inline-block;
                margin: 5px 2px;
                padding: 2px 15px;
                color: #000;
                background: #ddd;
                border: 1px solid transparent;
                text-decoration: none !important;
            }
            .circuit-export-wpr a:hover { border-color: #aaa; }

            .p-TabBar-tabIcon:before { font: normal normal normal 14px/1 FontAwesome; padding-right: 5px; }
            .p-TabBar-content > :nth-child(1) .p-TabBar-tabIcon:before { content: "\\f1de"; color: #b587f7; }
            .p-TabBar-content > :nth-child(2) .p-TabBar-tabIcon:before { content: "\\f00a"; color: #b33771; }
            .p-TabBar-content > :nth-child(3) .p-TabBar-tabIcon:before { content: "\\f039"; color: #ff9d85; }
            .p-TabBar-content > :nth-child(4) .p-TabBar-tabIcon:before { content: "\\f05a"; color: #6ea2c9; }

            .no-props .p-TabBar-content > :nth-child(2) .p-TabBar-tabLabel,
            .no-props .p-TabBar-content > :nth-child(2) .p-TabBar-tabIcon:before { color: #aaa; }
            .no-logs .p-TabBar-content > :nth-child(3) .p-TabBar-tabLabel,
            .no-logs .p-TabBar-content > :nth-child(3) .p-TabBar-tabIcon:before { color: #aaa; }

            .message { width: 90%; font-size: 26px; text-align: center; margin: 70px 0; font-weight: bold;}

            @media (max-width: 1000px) {
                .options { grid-template-columns: repeat(3, auto) !important; }
                .options > :nth-child(4) { display: none; }

                .transpilation-step { grid-template-columns: 35px auto 70px 70px 70px 70px 70px; }
                .transpilation-step > :nth-child(2) { font-size: 10px !important; }
                .transpilation-step > :nth-child(3) { display: none; }
            }

            @media (max-width:985px) {
                .title h1 { font-size: 26px; }
                .logo {margin : 0px 2px;}
                .transpilation-step { grid-template-columns: 35px auto 70px 70px 70px 70px; }
                .transpilation-step > :nth-child(6) { display: none; }

            }

            @media (max-width:800px) {
                
                
                .options { grid-template-columns: repeat(2, auto) !important; }
                .options > :nth-child(3) { display: none; }

                .transpilation-step { grid-template-columns: 35px auto 70px 70px 70px; }
                .transpilation-step > :nth-child(7) { display: none; }
            }

            @media (max-width:700px) {
                
                .summary-panel { grid-template-columns: repeat(1, auto) !important; }

                .property-set { width: 100% !important; }
                .property-items { display: none !important; }

                .circuit-export-wpr a {
                    font-size: 12px;
                    padding: 2px 6px;
                }

                .transpilation-step { grid-template-columns: 35px auto 70px 70px; }
                .transpilation-step > :nth-child(5) { display: none; }
            }

            @media (max-width:550px) {
                .logo {display: none;}
                .title {font-size : 14px;}
                .transpilation-step { grid-template-columns: 35px auto; }
                .transpilation-step > :nth-child(4) { display: none; }
                .transpilation-step > :nth-child(8) { display: none; }
            }

            .lds-spinner {
                position: relative;
                width: 80px;
                height: 80px;
                margin: 50px auto;
            }
            .lds-spinner div {
                transform-origin: 40px 40px;
                animation: lds-spinner 1.2s linear infinite;
            }
            .lds-spinner div:after {
                content: " ";
                display: block;
                position: absolute;
                top: 3px;
                left: 37px;
                width: 6px;
                height: 18px;
                border-radius: 20%;
                background: #aaa;
            }
            .lds-spinner div:nth-child(1) {
                transform: rotate(0deg);
                animation-delay: -1.1s;
            }
            .lds-spinner div:nth-child(2) {
                transform: rotate(30deg);
                animation-delay: -1s;
            }
            .lds-spinner div:nth-child(3) {
                transform: rotate(60deg);
                animation-delay: -0.9s;
            }
            .lds-spinner div:nth-child(4) {
                transform: rotate(90deg);
                animation-delay: -0.8s;
            }
            .lds-spinner div:nth-child(5) {
                transform: rotate(120deg);
                animation-delay: -0.7s;
            }
            .lds-spinner div:nth-child(6) {
                transform: rotate(150deg);
                animation-delay: -0.6s;
            }
            .lds-spinner div:nth-child(7) {
                transform: rotate(180deg);
                animation-delay: -0.5s;
            }
            .lds-spinner div:nth-child(8) {
                transform: rotate(210deg);
                animation-delay: -0.4s;
            }
            .lds-spinner div:nth-child(9) {
                transform: rotate(240deg);
                animation-delay: -0.3s;
            }
            .lds-spinner div:nth-child(10) {
                transform: rotate(270deg);
                animation-delay: -0.2s;
            }
            .lds-spinner div:nth-child(11) {
                transform: rotate(300deg);
                animation-delay: -0.1s;
            }
            .lds-spinner div:nth-child(12) {
                transform: rotate(330deg);
                animation-delay: 0s;
            }
            @keyframes lds-spinner {
                0% { opacity: 1; }
                100% { opacity: 0; }
            }
            </style>
            """
        )
        return final_style
