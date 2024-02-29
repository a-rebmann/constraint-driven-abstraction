from collections import Counter

import networkx as nx
from const import START_TOK, END_TOK, XES_NAME, XES_LIFECYCLE
from pm4py.statistics.start_activities.log import get as start_get
from pm4py.statistics.end_activities.log import get as end_get

from pm4py.statistics.eventually_follows.log import get as efg_get


def get_eventually_follows_graph(pm4py_log):
    efg_graph = efg_get.apply(pm4py_log)
    return efg_graph


def to_real_graph_encoded(log, with_start_and_end=False):
    G = nx.DiGraph()
    for item in log.dfg_dict.keys():
        G.add_nodes_from([
            (log.unique_event_classes.index(item[0]), {"count": log.activity_counts[item[0]]}),
            (log.unique_event_classes.index(item[1]), {"count": log.activity_counts[item[1]]}),
        ])
        G.add_edge(log.unique_event_classes.index(item[0]), log.unique_event_classes.index(item[1]), weight=1 / log.dfg_dict[item])
    if with_start_and_end:
        G.add_nodes_from([
            (START_TOK, {"count": log.num_cases})
        ])
        G.add_nodes_from([
            (END_TOK, {"count": log.num_cases})
        ])
        for s, c in log.start_activities.items():
            G.add_edge(START_TOK, log.unique_event_classes.index(s), weight=1 / c)
        for e, c in log.end_activities.items():
            G.add_edge(log.unique_event_classes.index(e), END_TOK, weight=1 / c)
    for ec in log.encoded_event_classes:
        if ec not in G.nodes:
            G.add_nodes_from([(ec, {"count": log.activity_counts[log.unique_event_classes[ec]]})])
    return G


def to_ef_graph_encoded(ef_graph, log, with_start_and_end=False):
    print(ef_graph)
    G = nx.DiGraph()
    for item in ef_graph.keys():
        G.add_nodes_from([
            (log.unique_event_classes.index(item[0]), {"count": log.activity_counts[item[0]]}),
            (log.unique_event_classes.index(item[1]), {"count": log.activity_counts[item[1]]}),
        ])
        G.add_edge(log.unique_event_classes.index(item[0]), log.unique_event_classes.index(item[1]), weight=1 / ef_graph[item])
    if with_start_and_end:
        G.add_nodes_from([
            (START_TOK, {"count": log.num_cases})
        ])
        G.add_nodes_from([
            (END_TOK, {"count": log.num_cases})
        ])
        for s, c in log.start_activities.items():
            G.add_edge(START_TOK, log.unique_event_classes.index(s), weight=1 / c)
        for e, c in log.end_activities.items():
            G.add_edge(log.unique_event_classes.index(e), END_TOK, weight=1 / c)
    for ec in log.encoded_event_classes:
        if ec not in G.nodes:
            G.add_nodes_from([(ec, {"count": log.activity_counts[log.unique_event_classes[ec]]})])
    return G


def to_real_graph(dfg, log, with_start_and_end=False):
    G = nx.DiGraph()
    for item in dfg.keys():
        G.add_nodes_from([
            (item[0], {"count": log.activity_counts[item[0]]}),
            (item[1], {"count": log.activity_counts[item[1]]}),
        ])
        G.add_edge(item[0], item[1], weight=1 / dfg[item])
    if with_start_and_end:
        G.add_nodes_from([
            (START_TOK, {"count": log.num_cases})
        ])
        G.add_nodes_from([
            (END_TOK, {"count": log.num_cases})
        ])
        for s, c in log.start_activities.items():
            G.add_edge(START_TOK, s, weight=1 / c)
        for e, c in log.end_activities.items():
            G.add_edge(e, END_TOK, weight=1 / c)
    return G


def to_real_simple_graph(dfg, pm4py_log):
    G = nx.DiGraph()
    for item in dfg.keys():
        G.add_nodes_from([
            (item[0]),
            (item[1]),
        ])
        G.add_edge(item[0], item[1], weight=1 / dfg[item])
    G.add_nodes_from([
        START_TOK
    ])
    G.add_nodes_from([
        END_TOK
    ])
    for s, c in start_get.get_start_activities(pm4py_log).items():
        G.add_edge(START_TOK, s, weight=1 / c)
    for e, c in end_get.get_end_activities(pm4py_log).items():
        G.add_edge(e, END_TOK, weight=1 / c)
    return G





def draw_dfg(G):
    pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    nx.draw_networkx(G, pos)
    #plt.show()


def merge_nodes(G, nodes, new_node, attr_dict=None, **attr):
    """
    Merges the selected `nodes` of the graph G into one `new_node`,
    meaning that all the edges that pointed to or from one of these
    `nodes` will point to or from the `new_node`.
    attr_dict and **attr are defined as in `G.add_node`.
    """

    G.add_node(new_node)  # Add the 'merged' node
    if len(nodes)>0:
        e_to_add = set()
        for n1, n2 in G.edges():
            # For all edges related to one of the nodes to merge,
            # make an edge going to or coming from the `new gene`.
            if n1 in nodes and n2 not in nodes:
                e_to_add.add((new_node, n2))
            elif n2 in nodes and n1 not in nodes:
                e_to_add.add((n1, new_node))
    for e in e_to_add:
        G.add_edge(e[0], e[1])
    for n in nodes:  # remove the merged nodes
        G.remove_node(n)


def get_dfg_concurrency(log):
    dfgs = list()
    for t in log:
        prev = t[0]
        for i in range(1, len(t)):
            if t[i][XES_LIFECYCLE] == "start":
                dfgs.append((prev[XES_NAME], t[i][XES_NAME]))
            if t[i][XES_LIFECYCLE] == "complete":
                prev = t[i]
    return dict(Counter(dfgs))
