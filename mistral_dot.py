import yaml
import collections
import sys
import pydot
import html

mapping_cb_colors = {
    "on-error": "#F26B7A",
    "on-success": "#97B503",
    "on-complete": "#E866E8",
}

# We need to keep the order from the dict loaded from yaml.load
# http://stackoverflow.com/questions/5121931/
# Order matters in direct mode
_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

yaml.add_representer(collections.OrderedDict, dict_representer)
yaml.add_constructor(_mapping_tag, dict_constructor)

def generate_label_html(task_name, action, task_default):
    html_tpl = '<FONT POINT-SIZE="10" COLOR="{}">{}</FONT>'
    html_tasks = []

    for task_type, task_action in task_default.iteritems():
        f = lambda x: x.keys()[0] if isinstance(x, dict) else x
        html_tasks += [html_tpl.format(mapping_cb_colors[task_type], f(task)) for task in task_action]

    html_str = (
        '<{}<BR />{}<BR /><FONT POINT-SIZE="10">{}</FONT>>'
    ).format(task_name, " ".join(html_tasks),
             html.escape(action).replace(".", "&#46;"))
    return html_str

def generate_direct_nodes(workflow_name, workflow, graph):
    cluster = pydot.Cluster(workflow_name.replace(".", "").replace("-", ""), label=workflow_name, style="dashed")

    for task_name, task in workflow.get("tasks", {}).iteritems():
        action = task.get("action", task.get("workflow", "noop"))
        tasks = task.get("default")
        tasks = {k: v for k, v in tasks.iteritems() if k not in task.keys()}
        html_str = generate_label_html(task_name, action, tasks)
        node = pydot.Node(workflow_name + "." + task_name, shape="box", label=html_str)
        cluster.add_node(node)

    graph.add_subgraph(cluster)


def generate_task_edges(workflow_name, workflow, task_name, task, graph):
    for callback_type in mapping_cb_colors.keys():
        cbtype = task.get(callback_type, [])
        if not cbtype: continue
        for callback in cbtype:
            if isinstance(callback, dict):
                callback = callback.keys()[0]
            child_name = workflow_name + "." + callback
            parent_name = workflow_name + "." + task_name
            child_found, parent_found = False, False
            for subgraph in graph.get_subgraph_list():
                for node in subgraph.get_node_list():
                    if node.get_name() == '"' + child_name + '"':
                        child_found = True
                    if node.get_name() == '"' + parent_name + '"':
                        parent_found = True
            if not child_found:
                child_name = callback
            if not parent_found:
                parent_name = task_name
            edge = pydot.Edge(parent_name, child_name, arrowhead="none",
                              color=mapping_cb_colors[callback_type])
            graph.add_edge(edge)


def generate_indirect_edges(workflow_name, workflow, task_name, task, graph):
    task_names = workflow.get("tasks").keys()
    if not any(key in mapping_cb_colors.keys() for key in task.keys()):
        try:
            task_next = task_names[task_names.index(task_name) + 1]
        except IndexError:
            return
        for key, value in workflow.get("tasks", {}).iteritems():
            for callback_type in mapping_cb_colors.keys():
                val = value.get(callback_type, [])
                if not val:
                    continue
                if any(task_next in v for v in val):
                    return
        child_name = workflow_name + "." + task_next
        parent_name = workflow_name + "." + task_name
        edge = pydot.Edge(parent_name, child_name, arrowhead="none")
        graph.add_edge(edge)

def generate_direct_edges(workflow_name, workflow, graph):
    for task_name, task in workflow.get("tasks", {}).iteritems():
        generate_indirect_edges(workflow_name, workflow, task_name, task, graph)
        generate_task_edges(workflow_name, workflow, task_name, task, graph)

def _add_task(workflows, name, filter_):
    for workflow_name, workflow in workflows.iteritems():
        task_defaults = workflow.get("task-defaults", {})
        for task_name, task in workflow.get("tasks", {}).iteritems():
            workflows[workflow_name]["tasks"][task_name]["default"] = {
                key: value for key, value in task_defaults.iteritems() if key in mapping_cb_colors.keys()
            }
    return workflows

def add_task_default(workflows):
    return _add_task(workflows, "default", mapping_cb_colors.keys())

def add_task_require(workflows):
    return _add_task(workflows, "required", ["required"])

def generate_graph(content):
    graph = pydot.Dot(graph_type="digraph", rankdir="TB")

    workflows = content.get("workflows", collections.OrderedDict(
        {k: v for k, v in content.iteritems() if isinstance(v, dict)}
    ))

    workflows = add_task_default(workflows)  # used only in type: direct
    workflows = add_task_require(workflows)  # used only in type: reverse
    for workflow_name, workflow in workflows.iteritems():
        generate_direct_nodes(workflow_name, workflow, graph)

    for workflow_name, workflow in workflows.iteritems():
        if workflow.get("type", "direct") == "direct":
            generate_direct_edges(workflow_name, workflow, graph)
    # TODO :)
    #   else:
    #        generate_reverse_edges(workflow_name, workflow, graph)

    graph.write_png('graph.png')

if __name__ == "__main__":
    try:
        yaml_file = sys.argv[1]
    except IndexError:
        exit(1)

    with open(yaml_file, "r") as handle:
        content = yaml.load(handle)

    generate_graph(content)
