# Qiskit Trebugger  <img src = 'imgs/logo.png' align = "center" height = "40px" width = "40px">

[![Unitary Fund](https://img.shields.io/badge/Supported%20By-UNITARY%20FUND-brightgreen.svg?style=for-the-badge)](http://unitary.fund)

A new take on debuggers for quantum transpilers. 
This repository presents a debugger for the **qiskit transpiler** in the form of a lightweight jupyter widget. Built as a project for the Qiskit Advocate Mentorship Program, Fall 2021. 


## Installation
1. To install the debugger using pip (a Python package manager), use - 

```bash
pip install qiskit-trebugger
``` 
PIP will handle the dependencies required for the package automatically and would install the latest version. 

2. To directly install via github follow the steps below after using `git clone`: 
 ```bash
 git clone https://github.com/TheGupta2012/qiskit-timeline-debugger.git
 ```
  - Make sure `python3` and `pip` are installed in your system. It is recommended to use a Python virtual environment to install and develop the debugger
  - `cd` into the `qiskit-timeline-debugger` directory
  - Use `pip install -r requirements.txt` to install the project dependencies
  - Next, execute `pip install .` command to install the debugger

## Usage Instructions

- After installing the package, import the `Debugger` instance from `qiskit_trebugger` package. 
- To run the debugger, simply replace the call to `transpile()` method of the qiskit module with `debug()` method of your debugger instance.
- The debugger provides two types of views namely *jupyter* and *cli*
- The **cli** view is the default view and recommender for users who want to use the debugger in a terminal environment 
- The **jupyter** view is recommended for usage in a jupyter notebook and provides a more interactive and detailed view of the transpilation process.
- For example - 

```python
from qiskit_ibm_runtime.fake_provider import FakeCasablanca
from qiskit.circuit.random import random_circuit 
from qiskit_trebugger import Debugger
import warnings

warnings.simplefilter('ignore')
debugger = Debugger()
backend = FakeCasablanca()
circuit = random_circuit(num_qubits = 3, depth = 2 , seed = 42)
# replace transpile call 
debugger.debug(circuit, view_type="jupyter", optimization_level = 2, backend = backend, initial_layout = list(range(4)))
``` 
- On calling the debug method, a new jupyter widget is displayed providing a complete summary and details of the transpilation process for circuits of < 2000 depth
- With an easy-to-use and responsive interface, users can quickly see which transpiler passes ran when, how they changed the quantum circuit, and what exactly changed.


## Feature Highlights

### `jupyter` view

<img src = 'imgs/jupyter/working.gif' width = '90%'>

#### 1. Circuit Evolution
- See your circuit changing while going through the transpilation process for a target quantum processor.
- A new custom feature enabling **visual diffs** for quantum circuits, allows you to see what exactly changed in your circuit using the matplotlib drawer of the qiskit module.

> Example 
- Circuit 1
<img src='imgs/jupyter/diff-1.png' height = "20%" width = "47%">

- Circuit 2
<img src='imgs/jupyter/diff-2.png' height = "40%" width = "70%">



#### 2. Circuit statistics
- Allows users to quickly scan through how the major properties of a circuit transform during each transpilation pass. 
- Helps to quickly isolate the passes which were responsible for the major changes in the resultant circuit.

<img src = 'imgs/jupyter/stats.png' height = '10%'>

#### 3. Transpiler Logs and Property sets
- Easily parse actions of the transpiler with logs emitted by each of its constituent passes and changes to the property set during transpilation
- Every log record is color coded according to the level of severity i.e. `DEBUG`, `INFO`, `WARNING` and `CRITICAL`.


<img src = 'imgs/jupyter/logs.png' height = '38%'>


### `cli` view

<img src="imgs/cli/working.gif" width = "90%">

#### 1. Transpilation Summary and Statistics
- A quick summary of the transpilation process for a given circuit.
- Faster access to information in the CLI view.

<img src="imgs/cli/full-view.png" width = "80%">

#### 2. Keyboard Shortcuts 

- The CLI view provides keyboard shortcuts for easy navigation and access to transpiler information.
- An **interactive status bar** at the bottom of the screen provides information about the current state of the debugger. 

<img src = "imgs/cli/status-main.png">
<img src = "imgs/cli/status-input.png">
<img src = "imgs/cli/status-idx.png">


#### 3. Transpiler Logs and Property sets

- Emits transpiler logs associated with each of the transpiler passes.
- Highlights addition to the property set and its changes during the transpilation process.

<img src = "imgs/cli/indexed-1.png" width = "90%"> 
<img src = "imgs/cli/indexed-2.png" width = "90%">

## Docs
We use the `pydoc` module to generate [project documentation](https://thegupta2012.github.io/qiskit-timeline-debugger/qiskit_trebugger.html)

## Demonstration and Blog
- Here is a [demonstration of TreBugger](https://drive.google.com/file/d/1oRstcov-OQWDpsM7Q53x7BfgFC-edtkT/view?usp=sharing) as a part of the final showcase for the Qiskit Advocate Mentorship Program, Fall 2021.
- You can also read some more details of our project in the [Qiskit medium blog](https://medium.com/qiskit/qiskit-trebugger-f7242066d368)

## Contributors 
- [Aboulkhair Foda](https://github.com/EgrettaThula)
- [Harshit Gupta](https://github.com/TheGupta2012)




