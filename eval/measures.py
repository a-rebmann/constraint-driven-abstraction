import math
from statistics import mean

from optimization.sim.simmatrix import convert_to_full_matrix
from const import POS
import networkx
from pm4py.objects.bpmn.bpmn_graph import BPMN
from sklearn.metrics import silhouette_score
import numpy as np
import pandas as pd

from model.pm.log import Log

"""
Graph based complexity measures proposed in 
Reijers, H.A., Mendling, J.: A study into the factors that influence the understandability of business process models. 
IEEE Trans. Syst. Man, Cybern.-Part A: Syst. Hum. 41(3), 449–462 (2011)
"""


def get_pairwise_distances(log: Log, similarity=False, full=True):
    unique_classes = log.unique_event_classes
    num_classes = len(unique_classes)
    matrix = np.empty((num_classes * (num_classes - 1)) // 2, dtype=np.double)
    counter = 0
    for i in range(num_classes - 1):
        for j in range(i + 1, num_classes):
            sim = 0
            co_occ = 0
            for case in log.cases:
                for subcase in case.subcases:
                    if {unique_classes[i], unique_classes[j]}.issubset(set(subcase.unique_event_classes)):
                        co_occ += 1
                        p_1 = subcase.get_att_for_label(unique_classes[i], POS)
                        p_2 = subcase.get_att_for_label(unique_classes[j], POS)
                        if len(p_1) == len(p_2):
                            pass
                        elif len(p_1) > len(p_2):
                            for _ in range(len(p_2), len(p_1) + 1):
                                p_2.append(0)
                        else:
                            for _ in range(len(p_1), len(p_2) + 1):
                                p_1.append(0)
                        if similarity:
                            sim += 1 - ((min([abs(x - y) for x, y in zip(p_1, p_2)])) / len(subcase.events))
                        else:
                            sim += ((min([abs(x - y) for x, y in zip(p_1, p_2)])) / len(subcase.events))
            if co_occ > 0:
                curr = sim / co_occ
                if curr < 0 or math.isnan(curr):
                    curr = 0.0
            else:
                if similarity:
                    curr = 0
                else:
                    curr = 1
            matrix[counter] = curr
            # print(matrix[counter], log.unique_event_classes[i],log.unique_event_classes[j],log.encoded_event_classes[i],log.encoded_event_classes[j], i,j)
            counter += 1
    if full:
        return convert_to_full_matrix(matrix, similarity)
    return matrix


def get_diameter(G):
    return networkx.diameter(G)


def get_density(G):
    """
    d = \frac{m}{n(n-1)}
    Parameters
    ----------
    G
    Returns
    -------
    """
    return networkx.density(G)


def get_silhouette_for_solution(log, dist, solution, inf_dfc=False):
    if inf_dfc:
        all_cls = log.unique_event_classes
        matrix = np.empty((len(all_cls), len(all_cls)), dtype=np.double)
        for i in range(len(all_cls)):
            for j in range(len(all_cls)):
                if i == j:
                    matrix[i, j] = 0
                    continue
                if (all_cls[i], all_cls[j]) in log.behavioral_profile["exclusive"]:
                    right = log.activity_counts[all_cls[i]]
                    left = log.activity_counts[all_cls[j]]
                else:
                    right = dist[(all_cls[i], all_cls[j])] if (all_cls[i], all_cls[j]) in dist.keys() else 0
                    left = dist[(all_cls[j], all_cls[i])] if (all_cls[j], all_cls[i]) in dist.keys() else 0
                curr_dist = 1 / (right + left + 1)
                matrix[i, j] = curr_dist
    else:
        matrix = get_pairwise_distances(log)
    idx_to_label = {}
    for i, sol in enumerate(solution):
        for idx in sol:
            idx_to_label[idx] = i
    labels = []
    for i in range(len(matrix)):
        if inf_dfc:
            labels.append(idx_to_label[log.unique_event_classes[i]])
        else:
            labels.append(idx_to_label[i])
    if len(set(labels)) == len(log.unique_event_classes) or len(set(labels)) == 1:
        return "NaN"
    score = silhouette_score(matrix, labels, metric='precomputed')
    return score


def get_acd(net):
    """
    Average connector degree is defined as the average incoming and outgoing sequence flows of all gateways
    and activities with at least two incoming or outgoing sequence flows
    Returns
    -------
    """
    all_arc_degrees = []
    for place in net.places:
        if len(place.in_arcs) >= 2 or len(place.out_arcs) >= 2:
            all_arc_degrees.append(len(place.in_arcs) + len(place.out_arcs))
    for trans in net.transitions:
        if len(trans.in_arcs) >= 2 or len(trans.out_arcs) >= 2:
            all_arc_degrees.append(len(trans.in_arcs) + len(trans.out_arcs))

    mean_degree = mean(all_arc_degrees) if all_arc_degrees else 0.0

    return 1.0 / (1.0 + max(mean_degree - 2, 0))


def get_acd_bpmn(bpmn_graph: BPMN):
    all_degrees = []
    for node in bpmn_graph.get_nodes():
        if isinstance(node, BPMN.ParallelGateway) or isinstance(node, BPMN.ExclusiveGateway) or isinstance(node,
                                                                                                           BPMN.InclusiveGateway):
            if len(node.get_out_arcs()) >= 2 or len(node.get_in_arcs()) >= 2:
                all_degrees.append(len(node.get_out_arcs()) + len(node.get_in_arcs()))
    mean_degree = mean(all_degrees) if all_degrees else 0.0
    return 1.0 / (1.0 + max(mean_degree - 2, 0))


def get_cfc_bpmn(bpmn_graph: BPMN, inverse=False):
    AND = []
    XOR = []
    OR = []
    for node in bpmn_graph.get_nodes():
        if isinstance(node, BPMN.ParallelGateway):
            if len(node.get_out_arcs()) >= 2:
                AND.append(1)
        if isinstance(node, BPMN.ExclusiveGateway):
            if len(node.get_out_arcs()) >= 2:
                XOR.append(len(node.get_out_arcs()))
        if isinstance(node, BPMN.InclusiveGateway):
            if len(node.get_out_arcs()) >= 2:
                OR.append((2 ** len(node.get_out_arcs())) - 1)
    if inverse:
        return 1.0 / (1.0 + sum(AND) + sum(XOR) + sum(OR))
    else:
        return sum(AND) + sum(XOR) + sum(OR)


def get_cfc(net, inverse=False):
    """
    CFC(P) = ∑CFCXOR−split (i) +
    (k)
    ∑CFCOR−split ( j) + j∈{OR−splits of P}
    (1)
    i∈{XOR−splits of P} ∑CFC
    AND−split k∈{AND-splits of P}
    Returns
    -------

    """
    AND = []
    XOR = []
    for place in net.places:
        if len(place.out_arcs) >= 2:
            XOR.append(len(place.out_arcs))
    for trans in net.transitions:
        if len(trans.out_arcs) >= 2:
            AND.append(1)
    if inverse:
        return 1.0 / (1.0 + sum(AND) + sum(XOR))
    else:
        return sum(AND) + sum(XOR)

def get_weak_order_matrix(log):
    unique_classes = list(set([event["concept:name"] for trace in log for event in trace]))
    wom = np.zeros(shape=(len(unique_classes), len(unique_classes)))
    for case in log:
        activities = [event["concept:name"] for event in case]
        for i in range(0, len(activities) - 1):
            for j in range(i + 1, len(activities)):
                wom[unique_classes.index(activities[i]), unique_classes.index(
                    activities[j])] += 1
    return pd.DataFrame(wom, columns=unique_classes, index=unique_classes)


def get_behavioral_profile(log):
    wom = get_weak_order_matrix(log)
    cols = wom.columns
    wom = wom.values
    wom_len = len(wom)
    res = np.empty((wom_len, wom_len), dtype=float)
    for i in range(wom_len):
        for j in range(wom_len):
            if i == j:  res[i, j] = 4; continue
            if wom[i, j] == 0 and wom[j, i] != 0: res[j, i] = 0; continue
            if wom[j, i] == 0 and wom[i, j] != 0: res[j, i] = 1; continue
            if wom[i, j] != 0 and wom[j, i] != 0: res[j, i] = 2; continue
            if wom[i, j] == 0 and wom[j, i] == 0: res[j, i] = 3; continue
    return pd.DataFrame(res, columns=cols, index=cols)


def behavioral_conformance(old_log, new_log, grouping):
    old_bp = get_behavioral_profile(old_log)
    new_log = get_behavioral_profile(new_log)
    abstracted_bp = get_behavioral_profile(old_log)
    single_to_group = {}
    group_to_new_activity = {}
    for col in new_log.columns:
        restored = frozenset(col.split("#"))
        for group in grouping:
            g = frozenset(group)
            if restored == g:
                group_to_new_activity[g] = col
    for group in grouping:
        g = frozenset(group)
        for elm in group:
            single_to_group[elm] = g
    for i in abstracted_bp.columns:
        for j in abstracted_bp.columns:
            if single_to_group[i] == single_to_group[j]:
                abstracted_bp.loc[i, j] = 2
            else:
                abstracted_bp.loc[i, j] = new_log.loc[(group_to_new_activity[single_to_group[i]]), (group_to_new_activity[single_to_group[j]])]
    numer = 0
    denom = 0
    for i in abstracted_bp.columns:
        for j in abstracted_bp.columns:
            denom += 1
            if (abstracted_bp.loc[i, j] == 0 or abstracted_bp.loc[i, j] == 1) and (old_bp.loc[i, j] == 2):
                numer += 1
            elif abstracted_bp.loc[i, j] == 3 and (old_bp.loc[i, j] < 3):
                numer += 1
    return 1 - numer/denom



def interruptions_variants(event_set, log, handle_loops=True):
    """
    """
    interrupted = dict()
    for variant in log.variants.keys():
        var_list = variant.split(',')
        var_list = [log.unique_event_classes.index(v) for v in var_list]
        if handle_loops and variant in log.split_loops.keys():
            var_lists = [var_list[i[0]:(i[1]+1)] for i in log.split_loops[variant]]
        else:
            var_lists = [var_list]
        for sub_variant in var_lists:
            if any(i in sub_variant for i in event_set):
                poses = [i for i, lab in enumerate(sub_variant) if lab in event_set]

                first = min(poses)
                last = max(poses)
                not_in = [(i, lab) for i, lab in enumerate(sub_variant[first:last]) if lab not in event_set]
                for ni in not_in:
                    if ni[1] not in interrupted.keys():
                        interrupted[ni[1]] = (set(), set())
                    interrupted[ni[1]][0].update(sub_variant[first:ni[0]])
                    interrupted[ni[1]][1].update(sub_variant[(ni[0]+1):last+1])
    return interrupted


def collect_and_evaluate_behavioral_distortions(group, log):
    interruptions = interruptions_variants(group, log)
    print(group)
    for interruption, precedes_succeeds in interruptions.items():
        if len(precedes_succeeds[0]) > len(precedes_succeeds[1]):
            diff = precedes_succeeds[0].difference(precedes_succeeds[1])
        else:
            diff = precedes_succeeds[1].difference(precedes_succeeds[0])

        only_preceeds = precedes_succeeds[0].intersection(diff)
        only_succeeds = precedes_succeeds[1].intersection(diff)
        if len(only_preceeds) > 0:
            print(interruption, only_preceeds, "p")
        if len(only_succeeds) > 0:
            print(interruption, only_succeeds, "s")