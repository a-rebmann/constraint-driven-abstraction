import sys
import time
from copy import deepcopy
from itertools import combinations, product
from queue import PriorityQueue

from const import CLASS_BASED, INSTANCE_BASED
from constraints.contraints_checking import check_all_constraints_case_based
from candidatecomputation.candidates import add_singletons
from model.group import Group, PrioritizedGroup, SimplePrioritizedGroup
from model.pm.log import Log
from optimization.sim.simfunction import group_wise_interleaving_variants, get_groupwise_interleaving_xor


def run_greedy(log: Log, constraints, handle_loops=True, handle_concurrent=True, frac_to_hold=1.0):
    print("Starting candidate computation")
    tic = time.perf_counter()
    # end_time is a tuple of bools that tell us if the endsize was reached or if a timeout was reached.
    groups, dist_map = get_candidates_and_distances(log=log, constraints=constraints, handle_loops=handle_loops,
                                                    handle_concurrent=handle_concurrent, frac_to_hold=frac_to_hold)
    toc = time.perf_counter()
    print(f"Computed candidate groups in {toc - tic:0.4f} seconds")
    # add_singletons(log, groups, dist_map, all_classes=True)
    return groups, dist_map


def get_candidates_and_distances(log: Log, constraints, handle_loops=True, handle_concurrent=True, frac_to_hold=1.0):
    groups, distance_map = greedy_candidate_computation(log=log,
                                                        constraints=constraints,
                                                        handle_loops=handle_loops,
                                                        handle_concurrent=handle_concurrent, frac_to_hold=frac_to_hold)
    distance_map = {group: distance_map[group].priority for group in distance_map.keys() if group in groups}
    groups = list(groups)
    return groups, distance_map


def greedy_candidate_computation(log, constraints, handle_loops=True, handle_concurrent=True, frac_to_hold=1.0):
    violation_dict = {}
    current_dist = sys.maxsize
    all_classes = log.encoded_event_classes
    overall_dist = len(all_classes)
    initial_event_sets = set([frozenset([cls]) for cls in all_classes])
    checked = dict()
    groups = set([frozenset([cls]) for cls in all_classes])
    discard = set()
    for group in groups:
        checked[group] = PrioritizedGroup(1, group, None)
    while current_dist > overall_dist and len(groups) > 1:
        b_prime = PriorityQueue()
        for event_set in set(frozenset.union(*event_set) for event_set in product(groups, initial_event_sets)):
            violation_dict[event_set] = {0: [0] * len(constraints),
                                             # violations of class based constraints
                                             1: [0] * len(constraints)}  # violations of instance based constraints
            if event_set in discard:
                continue
            if event_set in checked.keys():
                pi = checked[event_set]
            else:
                group_dist, co_occurrence = group_wise_interleaving_variants(event_set, log, handle_loops=handle_loops,
                                                                             handle_xor=False,
                                                                             handle_concurrent=handle_concurrent)
                if not co_occurrence:
                    continue
                pi = PrioritizedGroup(group_dist, event_set, None)
            pi.fulfils_requirements = check_all_constraints_case_based(log, pi.members, constraints,
                                                                       with_label=False,
                                                                       handle_loops=handle_loops,
                                                                       handle_xor=False,
                                                                       handle_concurrent=handle_concurrent,
                                                                       frac_to_hold=frac_to_hold,
                                                                       violation_dict=violation_dict)

            b_prime.put(pi)
            checked[event_set] = pi
        current_dist = sum(checked[group].priority for group in groups)
        pi = b_prime.get()
        discard.add(pi.members)
        # this is the new one
        # now we need to remove the subsets of the new one from event sets
        new_groups = deepcopy(groups)
        if pi.fulfils_requirements:
            for group in groups:
                if group.issubset(pi.members):
                    new_groups.remove(group)
                    for it in group:
                        if frozenset([it]) in initial_event_sets:
                            initial_event_sets.remove(frozenset([it]))
            new_groups.add(pi.members)
        if groups == new_groups:
            break
        groups = new_groups

        if not any(len(group) == 1 for group in groups):
            break
        overall_dist = sum(checked[group].priority for group in groups)
    result = deepcopy(groups)
    for group in groups:
        if not check_all_constraints_case_based(log, group, constraints,
                                                with_label=False,
                                                handle_loops=handle_loops,
                                                handle_xor=False,
                                                handle_concurrent=handle_concurrent,
                                                violation_dict=violation_dict):
            result.remove(group)
    return result, checked


def get_solution(groups, dist_map, log):
    r = PriorityQueue()
    count = 0
    for group in groups:
        count += 1
        p = SimplePrioritizedGroup(dist_map[group], group)
        r.put(p)
    solution_enc = set()
    best_dist = 0
    covered = set()
    while not r.empty():
        p = r.get()
        if any(idx in covered for idx in p.members):
            continue
        solution_enc.add(p.members)
        best_dist = best_dist + p.priority
        for idx in p.members:
            covered.add(idx)
    solution = [map_to_classes(sol, log) for sol in solution_enc]
    return solution_enc, solution, best_dist


def map_to_classes(sol_group, log):
    return [log.unique_event_classes[i] for i in sol_group]
