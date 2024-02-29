# GECCO: Constraint-driven Abstraction of Low-level Event Logs

<sub>
written by <a href="mailto:rebmann@informatik.uni-mannheim.de">Adrian Rebmann</a><br />
</sub>

## About
This repository contains the implementation, data, and evaluation scripts as described in the paper <i>GECCO: Constraint-driven Abstraction of Low-level Event Logs</i> by A. Rebmann, M. Weidlich, and H. van der Aa, published in the proceedings of the 38th IEEE International Conference on Data Engineering (ICDE 2022).

## Setup and Usage

### Installation instructions
**The project requires python >= 3.8**

0. (optional) create a virtual environment for the project 
1. install the dependencies in requirements.txt, e.g., using pip <code> pip install -r requirements.txt </code>
2. the prototype uses the Gurobi optimizer. There is a free trial license, which will be used automatically, if no other license is found on your machine. If the optimization problem is very large, though, the free version will not produce a result and the program will not complete. However, are free academic licenses that enable to run optimization problems of any size. See [Gurobi](https://www.gurobi.com/academia/academic-program-and-licenses/)
3. To display process models (directly-follows graphs) GraphViz is used, which may have to be installed on your system: <a href=https://graphviz.org/download/>GraphViz</a>

### Directories
The following default directories are used for input and output <b>please create them if not already there</b>:
* IN_PATH = 'resources/input/' 
* OUT_PATH = 'resources/output/' 

Adapt IN_PATH and OUT_PATH in <code>const.py</code>, if you want to load your input (and write your output) from (to) a different location

Place your input into IN_PATH.

<b>To give it a try, you should be able to run <code>python main.py</code> right after the environment is properly set up and directories are there, which will apply GECCO to the event log of the running example of the paper.</b>

### Usage 
1. Edit the configuration parameters in <code>main.py</code> if needed
2. Run the project using <code>python main.py</code>

## References
* [pm4py](https://pm4py.fit.fraunhofer.de) used for event log handling
* [Gurobi](https://www.gurobi.com/) used for optimization
* [SplitMiner2.0](http://apromore.org/research-lab/) used in the evaluation only to quantify complexity reduction of process models. <small>To use this you need to download the distribution and place the folder lib/ as well as the file sm2.jar into the root directory of the project. Additionally, create a new folder <code>models/</code> in the root directory.</small>



## Evaluation
Our approach was tested on a collection of  real-life event logs availbale from the 4TU data repository [4TU-Real-life-event-logs](https://data.4tu.nl/search?q=:keyword:%20%22real%20life%20event%20logs%22), please note the information and logs in <i>resources/raw/real/</i> as some were filtered to save storage.
Synthetic logs (included in this repository under <i>resources/raw/synthetic/</i>) were used for additional evaluation experiments, the results are available in the additional-evaluation.pdf.
To run the evaluation experiments the scripts 
* evaluation_synthetic.py
* evaluation_real.py

can be used. These run for quite some time, since several configurations, constraints, and logs are evaluated. When running either script for the first time, the importing of the logs takes additional time. We recommend to first run a config at a time, without parallelizing the evaluation runs to check if the environment is setup correctly.

The baseline comparison can be run with 
* evaluation_bl.py

Note that for the Graph querying baseline to run, [Neo4J](https://neo4j.com) needs to be installed and configured as follows


`host_name = "localhost",
port = 7687,
user = "neo4j",
password = "123qwe"`

