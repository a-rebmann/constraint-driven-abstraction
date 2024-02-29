import sys
from collections import deque
from itertools import chain, combinations
from queue import PriorityQueue

from model.group import Group, PrioritizedGroup
from model.pm.log import Log
from const import *
from tqdm import tqdm
from optimization.sim.simfunction import group_wise_interleaving_variants, get_groupwise_interleaving_xor
import time
from candidatecomputation.exclusive import check_xors, check_pred_succ_for_group
from constraints.contraints_checking import check_all_constraints_case_based, check_all_constraints_class_based


def powerset(iterable, f, l):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(f, l))


# checks anti-monotonic constraint violation
def check_amv(event_set, violation_dict, constraints):
    ckc = any(num > 0 and (constraints[INSTANCE_BASED][i][1] == MAX and not constraints[INSTANCE_BASED][i][2] == AVG) for i, num in
               enumerate(violation_dict[event_set][1])) or any(num > 0 and constraints[CLASS_BASED][i][1] == MAX for i, num in
                                                               enumerate(violation_dict[event_set][0]))
    return ckc


def check_constrains_for_singletons(log, constraints, handle_loops, handle_xor, handle_concurrent, frac_to_hold=1.0,
                                    violation_dict={}):
    exclude = set()
    for ec in log.encoded_event_classes:
        violation_dict[frozenset([ec])] = {0: [0] * len(constraints[CLASS_BASED]),
                                           # violations of class based constraints
                                           1: [0] * len(
                                               constraints[INSTANCE_BASED])}  # violations of instance based constraints
        if not (check_all_constraints_class_based(log, frozenset([ec]), constraints[CLASS_BASED],
                                                  violation_dict=violation_dict) and check_all_constraints_case_based(
                log, frozenset([ec]), constraints[INSTANCE_BASED], handle_loops=handle_loops,
                handle_xor=handle_xor,
                handle_concurrent=handle_concurrent, with_label=False,
                frac_to_hold=frac_to_hold, violation_dict=violation_dict)):
            #if mode == ANTI_MONO and check_amv(frozenset([ec]), violation_dict, constraints):
            exclude.add(ec)
    return exclude


def compute_candidate_groups(log: Log, constraints, constraint_dict, mode=ANTI_MONO, start_size=2, end_size=None,
                             incl_sub_sets=False, distance_notion=None,
                             beam_size=100, with_dfg=True, handle_loops=True, handle_xor=True, handle_concurrent=True,
                             fallback=False, frac_to_hold=1.0):
    violation_dict = {}

    exclude = check_constrains_for_singletons(log, constraint_dict, handle_loops=True, handle_xor=True,
                                              handle_concurrent=True, violation_dict=violation_dict)
    if mode == MONO and len(constraints) >= 1 and constraints[0][0] == XES_NAME:
        start_size = constraints[0][3]
    if mode == ANTI_MONO:
        if not fallback and len(exclude) > 0:
            return list(), dict(), (0, 2), violation_dict
    if with_dfg:
        print("Starting candidate computation on DFG")
        print("beam size is ", beam_size)
        tic = time.perf_counter()
        if beam_size < sys.maxsize:
            groups, dist_map, end_time = recurse_variant_dfg_beam(log=log,
                                                                  constraints=constraint_dict, beam_size=beam_size,
                                                                  distance_notion=distance_notion,
                                                                  handle_loops=handle_loops, handle_xor=handle_xor,
                                                                  handle_concurrent=handle_concurrent, mode=mode,
                                                                  start_size=start_size,
                                                                  end_size=end_size, time_check=time_out,
                                                                  frac_to_hold=frac_to_hold,
                                                                  violation_dict=violation_dict)
        else:
            groups, dist_map, end_time = recurse_variant_dfg(log=log,
                                                             constraints=constraint_dict,
                                                             distance_notion=distance_notion,
                                                             handle_loops=handle_loops, handle_xor=handle_xor,
                                                             handle_concurrent=handle_concurrent, mode=mode,
                                                             start_size=start_size,
                                                             end_size=end_size, time_check=time_out,
                                                             frac_to_hold=frac_to_hold, violation_dict=violation_dict)
        toc = time.perf_counter()
        print(f"Completed candidate computation on DFG after {toc - tic:0.4f} seconds")
        groups = list(groups)
    else:
        print("Starting candidate computation")
        tic = time.perf_counter()
        # end_time is a tuple of bools that tell us if the endsize was reached or if a timeout was reached.
        groups, dist_map, end_time = get_candidates_and_distances(log=log, constraints=constraint_dict,
                                                                  incl_sub_sets=incl_sub_sets,
                                                                  distance_notion=distance_notion, mode=mode,
                                                                  start_size=start_size,
                                                                  end_size=end_size, handle_loops=handle_loops,
                                                                  handle_xor=handle_xor,
                                                                  handle_concurrent=handle_concurrent,
                                                                  frac_to_hold=frac_to_hold,
                                                                  violation_dict=violation_dict)
        toc = time.perf_counter()
        print(f"Computed candidate groups in {toc - tic:0.4f} seconds")
    if handle_xor:
        xor_groups = check_xors(log, groups)
        for xor_group in xor_groups:
            violation_dict[xor_group.members] = {0: [0] * len(constraint_dict[CLASS_BASED]),
                                                 # violations of class based constraints
                                                 1: [0] * len(constraint_dict[
                                                                  INSTANCE_BASED])}  # violations of instance based constraints
            if not len(xor_group.members) > end_size - 1 and check_all_constraints_class_based(log, xor_group.members,
                                                                                               constraint_dict[
                                                                                                   CLASS_BASED],
                                                                                               violation_dict=violation_dict):
                group_dist = get_groupwise_interleaving_xor(xor_group.members, log, handle_loops=handle_loops,
                                                            handle_concurrent=handle_concurrent)
                groups.append(xor_group.members)
                dist_map[xor_group.members] = group_dist
    if fallback:
        add_singletons(log, groups, dist_map, all_classes=True)
    else:
        to_consider = set(log.encoded_event_classes)
        to_consider = to_consider.difference(exclude)
        for to_add in to_consider:
            singleton = frozenset([to_add])
            groups.append(singleton)
            dist_map[singleton] = 1
    return groups, dist_map, end_time, violation_dict


def add_singletons(log, groups, dist_map, all_classes=False):
    if len(groups) == 0:
        return list()
    if all_classes:
        all_covered_by_groups = log.encoded_event_classes
    else:
        all_covered_by_groups = list(frozenset.union(*groups))
    singletons = []
    for cls in all_covered_by_groups:
        dist_map[frozenset([cls])] = 1
        singletons.append(frozenset([cls]))
    groups.extend(singletons)
    return all_covered_by_groups


def get_candidates_and_distances(log: Log, constraints, incl_sub_sets=False, distance_notion=None,
                                 mode=ANTI_MONO, start_size=2, end_size=None,
                                 handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1.0,
                                 violation_dict=None):
    # TODO for exactly and min check target value
    distance_map = {}
    event_sets = list(powerset(log.encoded_event_classes, start_size, start_size + 1))
    event_sets = [Group(frozenset(eventset)) for eventset in event_sets]
    groups, end_time = recurse_variant_while(log=log, event_sets=event_sets,
                                             constraints=constraints, dist_map=distance_map,
                                             distance_notion=distance_notion, incl_sub_sets=incl_sub_sets,
                                             handle_loops=handle_loops, handle_xor=handle_xor,
                                             handle_concurrent=handle_concurrent, mode=mode,
                                             end_size=end_size, time_check=time_out, frac_to_hold=frac_to_hold,
                                             violation_dict=violation_dict)

    groups = list(groups)
    return groups, distance_map, end_time


def recurse_variant_while(log, event_sets, constraints, dist_map, incl_sub_sets,
                          distance_notion=None,
                          handle_loops=True, handle_xor=True, handle_concurrent=True, mode=NON_MONO, end_size=None,
                          time_check=7200, frac_to_hold=1.0, violation_dict=None):
    starttime = time.time()
    groups = set()
    while len(event_sets) != 0:
        still_alive = list()
        for f_set in tqdm(event_sets):

            if time.time() - starttime > time_check:
                return groups, (False, True)
            # f_set = frozenset(event_set)
            group_dist, co_occurrence = group_wise_interleaving_variants(f_set.members, log, handle_loops=handle_loops,
                                                                         handle_xor=handle_xor,
                                                                         handle_concurrent=handle_concurrent)
            if not co_occurrence:
                continue
            if mode != ANTI_MONO:
                still_alive.append(f_set)
            violation_dict[f_set.members] = {0: [0] * len(constraints[CLASS_BASED]),
                                             # violations of class based constraints
                                             1: [0] * len(constraints[
                                                              INSTANCE_BASED])}  # violations of instance based constraints
            if f_set.skip_checking or (check_all_constraints_class_based(log, f_set.members, constraints[CLASS_BASED],
                                                                         violation_dict=violation_dict) and check_all_constraints_case_based(
                log, f_set.members, constraints[INSTANCE_BASED],
                with_label=False,
                handle_loops=handle_loops,
                handle_xor=handle_xor,
                handle_concurrent=handle_concurrent,
                on_log=False, frac_to_hold=frac_to_hold, violation_dict=violation_dict)):
                if mode == MONO:
                    f_set.skip_checking = True
                if mode == ANTI_MONO:
                    still_alive.append(f_set)
                dist_map[f_set.members] = group_dist
                groups.add(f_set.members)
                if handle_xor:
                    check_pred_succ_for_group(log, f_set.members)

                if not incl_sub_sets:
                    groups_copy = groups.copy()
                    for group in groups_copy:
                        if f_set.issuperset(group) and len(group) == len(f_set) - 1:
                            groups.discard(group)
            if mode == ANTI_MONO and not check_amv(f_set.members, violation_dict, constraints):
                still_alive.append(f_set)
        if len(still_alive) == 0:
            return groups, (False, False)
        new_sets = set()
        if end_size is not None and len(next(iter(still_alive)).members) >= end_size - 1:
            return groups, (True, False)
        for a, b in combinations(still_alive, 2):
            n = a.members.union(b.members)
            if len(n) == (len(a.members) + 1):
                new_sets.add(Group(n, a.skip_checking or b.skip_checking))
        event_sets = new_sets
    return groups, (False, False)


def recurse_variant_dfg(log, constraints, distance_notion=None,
                        handle_loops=True, handle_xor=True, handle_concurrent=True, mode=NON_MONO, start_size=2,
                        end_size=None,
                        time_check=7200, frac_to_hold=1.0, violation_dict=None):
    if start_size > 2:
        paths = list()
        for n in log.encoded_event_classes:
            paths.extend(findpaths(log.dfg_encoded, n, dst=start_size).values())
        event_sets = [PrioritizedGroup(1000, frozenset(path), path, False) for path in
                      paths]
    else:
        event_sets = [PrioritizedGroup(1000, frozenset(
            [log.unique_event_classes.index(item[0]), log.unique_event_classes.index(item[1])]),
                                       [log.unique_event_classes.index(item[0]),
                                        log.unique_event_classes.index(item[1])],
                                       False) for item in
                      log.dfg_dict.keys() if item[0] != item[1]]
    starttime = time.time()
    groups = set()
    dist_map = {}
    while len(event_sets) != 0:
        still_alive = list()
        for f_set in tqdm(event_sets):

            if time.time() - starttime > time_check:
                return groups, dist_map, (False, True)
            group_dist, co_occurrence = group_wise_interleaving_variants(f_set.members, log, handle_loops=handle_loops,
                                                                         handle_xor=handle_xor,
                                                                         handle_concurrent=handle_concurrent)
            if not co_occurrence:
                continue
            if mode != ANTI_MONO:
                still_alive.append(f_set)
            violation_dict[f_set.members] = {0: [0] * len(constraints[CLASS_BASED]),
                                             # violations of class based constraints
                                             1: [0] * len(constraints[
                                                              INSTANCE_BASED])}  # violations of instance based constraints
            if f_set.skip_checking or (check_all_constraints_class_based(log, f_set.members, constraints[CLASS_BASED],
                                                                         violation_dict=violation_dict) and check_all_constraints_case_based(
                log, f_set.members, constraints[INSTANCE_BASED],
                with_label=False,
                handle_loops=handle_loops,
                handle_xor=handle_xor,
                handle_concurrent=handle_concurrent,
                on_log=False, frac_to_hold=frac_to_hold, violation_dict=violation_dict)):
                if mode == MONO:
                    f_set.skip_checking = True
                if mode == ANTI_MONO:
                    still_alive.append(f_set)
                dist_map[f_set.members] = group_dist
                groups.add(f_set.members)
                if handle_xor:
                    check_pred_succ_for_group(log, f_set.members)
            if mode == ANTI_MONO and not check_amv(f_set.members, violation_dict, constraints):
                still_alive.append(f_set)
        if len(still_alive) == 0:
            return groups, dist_map, (False, False)
        new_sets = set()
        if end_size is not None and len(next(iter(still_alive)).members) >= end_size - 1:
            return groups, dist_map, (True, False)

        for p in still_alive:
            for succ in log.dfg_encoded.successors(p.path[-1]):
                if is_not_visited(succ, p.path):
                    new_sets.add(
                        PrioritizedGroup(1000, p.members.union(frozenset([succ])), p.path + [succ], p.skip_checking))
            for pred in log.dfg_encoded.predecessors(p.path[0]):
                if is_not_visited(pred, p.path):
                    new_sets.add(
                        PrioritizedGroup(1000, p.members.union(frozenset([pred])), [pred] + p.path, p.skip_checking))

        event_sets = new_sets
        if len(still_alive) == 0:
            return groups, dist_map, (False, False)

    return groups, dist_map, (False, False)


def recurse_variant_dfg_beam(log, constraints, beam_size=1000,
                             distance_notion=None,
                             handle_loops=True, handle_xor=True, handle_concurrent=True, mode=NON_MONO, start_size=2,
                             end_size=None,
                             time_check=7200, frac_to_hold=1.0, violation_dict=None):
    if start_size > 2:
        paths = list()
        for n in log.encoded_event_classes:
            paths.extend(findpaths(log.dfg_encoded, n, dst=start_size).values())
        event_sets = [PrioritizedGroup(1000, frozenset(path), path, False) for path in
                      paths]
    else:
        event_sets = [PrioritizedGroup(1000, frozenset(
            [log.unique_event_classes.index(item[0]), log.unique_event_classes.index(item[1])]),
                                       [log.unique_event_classes.index(item[0]),
                                        log.unique_event_classes.index(item[1])],
                                       False) for item in
                      log.dfg_dict.keys() if item[0] != item[1]]
    starttime = time.time()
    groups = set()
    dist_map = {}
    while len(event_sets) != 0:

        b_prime = PriorityQueue()
        for f_set in tqdm(event_sets):

            if time.time() - starttime > time_check:
                return groups, dist_map, (False, True)
            group_dist, co_occurrence = group_wise_interleaving_variants(f_set.members, log, handle_loops=handle_loops,
                                                                         handle_xor=handle_xor,
                                                                         handle_concurrent=handle_concurrent)
            if not co_occurrence:
                continue
            violation_dict[f_set.members] = {0: [0] * len(constraints[CLASS_BASED]),
                                             # violations of class based constraints
                                             1: [0] * len(constraints[
                                                              INSTANCE_BASED])}  # violations of instance based constraints
            f_set.priority = group_dist
            if not f_set.skip_checking:
                f_set.fulfils_requirements = check_all_constraints_class_based(log, f_set.members,
                                                                               constraints[CLASS_BASED],
                                                                               violation_dict=violation_dict) and check_all_constraints_case_based(
                    log, f_set.members, constraints[INSTANCE_BASED],
                    with_label=False,
                    handle_loops=handle_loops,
                    handle_xor=handle_xor,
                    handle_concurrent=handle_concurrent,
                    on_log=False, frac_to_hold=frac_to_hold, violation_dict=violation_dict)
                if mode == ANTI_MONO and check_amv(f_set.members, violation_dict, constraints) and not f_set.fulfils_requirements:
                    continue
            else:
                f_set.fulfils_requirements = True
            b_prime.put(f_set)
        still_alive = list()
        beam_check = 0
        while (not b_prime.empty()) and beam_check < beam_size:
            pi = b_prime.get()
            if mode == ANTI_MONO and not pi.fulfils_requirements:
                continue
            still_alive.append(pi)
            if pi.fulfils_requirements:
                if mode == MONO:
                    pi.skip_checking = True
                groups.add(pi.members)
                dist_map[pi.members] = pi.priority
                if handle_xor:
                    check_pred_succ_for_group(log, pi.members)
            beam_check += 1
        if len(still_alive) == 0:
            return groups, dist_map, (False, False)
        if end_size is not None and len(next(iter(still_alive)).members) >= end_size - 1:
            return groups, dist_map, (True, False)
        new_sets = set()

        for p in still_alive:
            for succ in log.dfg_encoded.successors(p.path[-1]):
                if is_not_visited(succ, p.path):
                    new_sets.add(
                        PrioritizedGroup(1000, p.members.union(frozenset([succ])), p.path + [succ], p.skip_checking))
            for pred in log.dfg_encoded.predecessors(p.path[0]):
                if is_not_visited(pred, p.path):
                    new_sets.add(
                        PrioritizedGroup(1000, p.members.union(frozenset([pred])), [pred] + p.path, p.skip_checking))

        event_sets = new_sets
        if len(still_alive) == 0:
            return groups, dist_map, (False, False)

    return groups, dist_map, (False, False)


def map_to_classes(group, log):
    return [log.unique_event_classes[i] for i in group.members]


# Utility function to check if current
# vertex is already present in path
def is_not_visited(x: int, path: list()) -> int:
    size = len(path)
    for i in range(size):
        if path[i] == x:
            return False
    return True


def findpaths(G, src,
              dst: int):
    # Create a queue which stores
    # the candidates
    q = deque()
    res = dict()
    # Path vector to store the current path
    path = [src]
    q.append(path.copy())

    while q:
        path = q.popleft()
        last = path[-1]

        # If last vertex is the desired distance
        # then add the path
        if len(path) == dst:
            res[frozenset(path)] = path
        if len(path) > dst:
            return res
        # Traverse to all the nodes connected to
        # current vertex and push new path to queue
        for n in G.neighbors(last):
            if is_not_visited(n, path):
                newpath = path.copy()
                newpath.append(n)
                q.append(newpath)
    return res
