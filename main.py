import os
import sys
from copy import deepcopy

from eval.greedy_bl import run_greedy, get_solution
from model.pm.dfg_util import get_dfg_concurrency
from readwrite import read, serialize_event_log, deserialize_event_log, write_xes, load_precomputed, \
    store_precomputed
from model.pm.log import from_pm4py_event_log, Log
from const import *
from postprocessing.create_log import create_mapping_from_groups, apply_mapping_to_log
from pm4py.visualization.dfg import visualizer as dfg_visualization
from optimization.knuth.all_solutions import compute_all_valid_solutions, find_best_solution_with_group_wise_sim
from optimization.optimization import create_and_solve_ip
from candidatecomputation.candidates import compute_candidate_groups
from eval.discovery import dfg
from constraints.contraints_checking import check_constraint
from candidatecomputation.exclusive import handle_singleton_xor_sets
from eval.config import Config
from feedback.feedback import provide_feedback_about_constraints

import time

########################
# Parameters
########################

"""
Constraints are of shape (attribute | bound | aggregation function | target value)
"""
# NUMBER OF GROUPS, CAN BE USED TO PROVIDE A GUARANTEE ON THE SIZE ENTIRE GROUPING. use 'NUM_GROUPS' as the attribute!

# TIME IS HANDLED USING 'SECONDS' AS THE TIME UNIT

# RUNNING EXAMPLE
RUNNING_EXAMPLE_CONSTRAINT = [(XES_RESOURCE, MAX, None, 1)]

# CONSTRAINT FOR WHICH NO SOLUTION IS POSSIBLE
EXAMPLE_CONSTRAINT_INFEASIBLE = [(SINCE_LAST, MAX, SUM, 9*60)]

CONFIG = Config(efficient=True, guarantees=RUNNING_EXAMPLE_CONSTRAINT, distance_notion=INTER_GROUP_INTERLEAVING,
                greedy=False,
                optimal_solution=True,
                create_mapping=True, do_projection=True, only_complete=False, xes=True, handle_xor=True,
                handle_loops=True, handle_concurrent=True)


def run(config=CONFIG):
    for (dir_path, dir_names, filenames) in os.walk(IN_PATH):
        for filename in filenames:
            if filename.startswith('.'):
                continue
            # Getting the log
            event_log = deserialize_event_log(config.log_ser_path, filename.replace(".xes", ""))
            if not event_log:
                event_log = prepare_single_log(IN_PATH, filename, config.log_ser_path)
            abstracted_log = abstract_log(event_log, config)
            dfg(event_log.pm4py, viz=True)
            try:
                dfgs = get_dfg_concurrency(abstracted_log)
                gviz = dfg_visualization.apply(dfgs, log=abstracted_log,
                                               variant=dfg_visualization.Variants.FREQUENCY,
                                               parameters={
                                                   dfg_visualization.frequency.Parameters.MAX_NO_EDGES_IN_DIAGRAM: 1000})
                dfg_visualization.view(gviz)
            except KeyError:
                print("The DFG of the abstracted log would be identical.")


def abstract_log(event_log: Log, config) -> object:
    """
    Parameters
    ----------
    """
    print("Event log " + event_log.name + " has " + str(len(event_log.unique_event_classes)) + " event classes.")
    if config.handle_xor:
        handle_singleton_xor_sets(event_log)
    start_size, end_size, lower_k, upper_k, mode, constraint_dict = check_constraint(event_log, config.guarantees)
    print("Start size: " + str(start_size), "End size: " + str(end_size),
          "Lower bound for number of classes: " + str(lower_k), "Upper bound for number of classes: " + str(upper_k),
          mode)
    print(constraint_dict)
    groups, dist_map = load_precomputed(event_log, config)
    violation_dict = None
    if not groups or len(dist_map) == 0:
        if config.greedy:
            groups, dist_map = run_greedy(event_log, config.guarantees, handle_loops=config.handle_loops,
                                          handle_concurrent=config.handle_concurrent, frac_to_hold=config.frac_to_hold)
        else:
            groups, dist_map, _, violation_dict = compute_candidate_groups(event_log, config.guarantees,
                                                           constraint_dict=constraint_dict,
                                                           mode=mode,
                                                           start_size=start_size, end_size=end_size,
                                                           incl_sub_sets=(not config.greedy),
                                                           distance_notion=config.distance_notion,
                                                           beam_size=config.beam_size,
                                                           with_dfg=config.efficient,
                                                           handle_loops=config.handle_loops,
                                                           handle_xor=config.handle_xor,
                                                           handle_concurrent=config.handle_concurrent,
                                                           frac_to_hold=config.frac_to_hold)
        if config.store_groups:
            store_precomputed(event_log, config, groups, dist_map)

    if len(groups) == 0:
        print("No groups found in the log for the given constraints.\nTerminating...")
        if violation_dict is not None:
            provide_feedback_about_constraints(violation_dict, constraint_dict, event_log)
        return event_log.pm4py
    if config.greedy:
        solution_enc, solution, best_dist = get_solution(groups, dist_map, event_log)
    elif config.optimal_solution:
        all_covered_by_groups = list(event_log.encoded_event_classes)
        tic = time.perf_counter()
        try:
            solution, best_dist = create_and_solve_ip(all_covered_by_groups, len(all_covered_by_groups), groups,
                                                      dist_map,
                                                      event_log,
                                                      lower_k=lower_k, upper_k=upper_k)
            [[event_log.unique_event_classes.index(i) for i in sol] for sol in solution]
        except TypeError:
            print("No optimal solution possible!")
            if violation_dict is not None:
                provide_feedback_about_constraints(violation_dict, constraint_dict, event_log)
            return event_log.pm4py
        # UNCOMMENT THE FOLLOWING LINES IF YOU WANT FEEDBACK IN ANY CASE
        # if violation_dict is not None:
        #     provide_feedback_about_constraints(violation_dict, constraint_dict, event_log)
        toc = time.perf_counter()
        print(f"Computed optimal solution in {toc - tic:0.4f} seconds")
    else:
        all_covered_by_groups = list(frozenset.union(*groups))
        print("The candidates cover " + str(len(all_covered_by_groups)) + " event classes")
        tic = time.perf_counter()
        matrix, possible_sols = compute_all_valid_solutions(groups, all_covered_by_groups, k=len(all_covered_by_groups))
        solution = find_best_solution_with_group_wise_sim(matrix, dist_map, possible_sols, all_covered_by_groups,
                                                          event_log)
        toc = time.perf_counter()
        print(f"Computed optimal solution in {toc - tic:0.4f} seconds")
        if violation_dict is not None:
            provide_feedback_about_constraints(violation_dict, constraint_dict)
    if config.create_mapping:
        mapping = create_mapping_from_groups(event_log, solution, by_len=False)
        if config.do_projection:
            tic = time.perf_counter()
            pm4py_copy = deepcopy(event_log.pm4py)
            abstracted_log = apply_mapping_to_log(mapping, pm4py_copy, only_complete=config.only_complete)
            toc = time.perf_counter()
            print(f"Projected log in {toc - tic:0.4f} seconds")
            # export the event log as an XES file
            if config.export_xes:
                write_xes(OUT_PATH, event_log.name + '_abstracted', abstracted_log)
            return abstracted_log
    return event_log.pm4py


def prepare_single_log(input_path, log_file, output_path):
    tic = time.perf_counter()
    log, _ = read(input_path, log_file, log_to_case_id, log_to_label, log_to_timestamp)
    event_log = from_pm4py_event_log(log, log_file.replace(".xes", "").replace(".csv", ""))
    # event_log.add_roles(True, True) #to add business objects / actions that are extracted. Requires extraction package!
    serialize_event_log(output_path, event_log)
    toc = time.perf_counter()
    print(f"Prepared log in {toc - tic:0.4f} seconds")
    return event_log


if __name__ == "__main__":
    run()
    sys.exit(0)
