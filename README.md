# mistral-graph
Tool for visualising a mistral v2 workflow (openstack)

Some example of the output  

![multiple workflow and default tasks](/example/example_default_tasks.png)

![workflow attributes](/example/example_workflow.png)

![workflow example](/example/example.png)

## Usage

    python mistral_dot.py example.yaml

This will create a new png file named `graph.png`.
Currently it only supports direct workflows.

## Installation

Requires pydot

    pip install pydot

## TODO

- Some parts of the code are ugly.
- Need more comments.

