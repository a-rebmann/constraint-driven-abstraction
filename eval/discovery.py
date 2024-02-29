import os
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.visualization.petrinet import visualizer as pn_visualizer
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.visualization.dfg import visualizer as dfg_visualization


def inductive(log, out_dir):
    net, initial_marking, final_marking = inductive_miner.apply(log)
    gviz = pn_visualizer.apply(net, initial_marking, final_marking)
    pn_visualizer.save(gviz, os.path.join(out_dir, "inductive.png"))


def dfg(log, viz=False):
    dfg_res = dfg_discovery.apply(log)
    if viz:
        gviz = dfg_visualization.apply(dfg_res, log=log,
                                       variant=dfg_visualization.Variants.FREQUENCY,
                                       parameters={dfg_visualization.frequency.Parameters.MAX_NO_EDGES_IN_DIAGRAM: 1000})
        dfg_visualization.view(gviz)
    else:
        return dict(dfg_res)
