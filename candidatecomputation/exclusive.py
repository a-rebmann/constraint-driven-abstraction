from model.pm.log import Log
from itertools import product, combinations
from model.pm.dfg_util import merge_nodes
from model.group import XORGroup


def handle_singleton_xor_sets(log: Log):
    for ec in log.encoded_event_classes:
        check_pred_succ_for_group(log, frozenset({ec}))


def check_pred_succ_for_group(log: Log, group):
    if len(group) == 1:
        succ_1 = frozenset(log.dfg_encoded.successors(n=next(iter(group))))
        pred_1 = frozenset(log.dfg_encoded.predecessors(n=next(iter(group))))
    else:
        H = log.dfg_encoded.copy(as_view=False)
        node_1 = str(group)
        merge_nodes(H, group, node_1)
        succ_1 = frozenset(H.successors(n=node_1))
        pred_1 = frozenset(H.predecessors(n=node_1))
    if (pred_1, succ_1) not in log.pre_succ_to_groups.keys():
        log.pre_succ_to_groups[(pred_1, succ_1)] = set([group])
    log.pre_succ_to_groups[(pred_1, succ_1)].add(group)


def check_xors(log: Log, groups):
    additional_xor_groups = set()
    for key, value in log.pre_succ_to_groups.items():
        if len(value) > 1:
            recurse_xor(log, additional_xor_groups, value, key, groups)
    for group in additional_xor_groups:
        if len(group.members) not in log.xor_sets.keys():
            log.xor_sets[len(group.members)] = set()
        log.xor_sets[len(group.members)].add(group)
    return additional_xor_groups


def recurse_xor(log: Log, additional_xor_groups, still_alive, pre_succ, groups):
    if len(still_alive) == 0:
        return
    to_check = list(combinations(still_alive, 2))
    for combi in to_check:
        if all((log.unique_event_classes[c1], log.unique_event_classes[c2]) in log.behavioral_profile[
            "exclusive"] for c1, c2 in product(combi[0], combi[1])):
            to_try = still_alive.copy()
            to_try.remove(combi[0])
            to_try.remove(combi[1])
            merge = frozenset.union(*combi)
            if pre_succ[1].union(combi[0]) in groups and pre_succ[1].union(combi[1]) in groups and pre_succ[1].union(combi[0]) in groups and pre_succ[1].union(combi[1]) in groups:
                additional_xor_groups.add(XORGroup(pre_succ[0].union(pre_succ[1]).union(merge), pre_succ[1], pre_succ[0]))
            elif pre_succ[0].union(combi[0]) in groups and pre_succ[0].union(combi[1]) in groups:
                additional_xor_groups.add(XORGroup(pre_succ[0].union(merge), pre_succ[1], pre_succ[0]))
            elif pre_succ[1].union(combi[0]) in groups and pre_succ[1].union(combi[1]) in groups:
                additional_xor_groups.add(XORGroup(pre_succ[1].union(merge), pre_succ[1], pre_succ[0]))
            to_try.add(merge)
            additional_xor_groups.add(XORGroup(merge, pre_succ[1], pre_succ[0]))
            recurse_xor(log, additional_xor_groups, to_try, pre_succ, groups)


def check_complex_xor_set(log: Log, event_set_1, event_set_2):
    if len(event_set_1.intersection(event_set_2)) > 0:
        return False
    if all((log.unique_event_classes[c1], log.unique_event_classes[c2]) in log.behavioral_profile["exclusive"] for
           c1, c2 in product(event_set_1, event_set_2)):
        H = log.dfg_encoded.copy(as_view=False)
        node_1 = str(event_set_1)
        node_2 = str(event_set_2)
        merge_nodes(H, event_set_1, node_1)
        merge_nodes(H, event_set_2, node_2)
        succ_1 = frozenset(H.successors(n=node_1))
        pred_1 = frozenset(H.predecessors(n=node_1))
        succ_2 = frozenset(H.successors(n=node_2))
        pred_2 = frozenset(H.predecessors(n=node_2))
        if succ_1 == succ_2 and pred_1 == pred_2:
            xor_l = len(event_set_1) + len(event_set_2)
            if xor_l not in log.xor_sets.keys():
                log.xor_sets[xor_l] = set()
            log.xor_sets[xor_l].add(XORGroup(frozenset(event_set_1.union(event_set_2)), succ_1, pred_1))
            print("MERGE", frozenset(event_set_1.union(event_set_2)))
            return True
    return False
