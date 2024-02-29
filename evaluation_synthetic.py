import multiprocessing
import os
import pickle
import subprocess
import sys
import time
import csv
from copy import deepcopy
from statistics import median

from lxml.etree import XMLSyntaxError

from eval.greedy_bl import run_greedy, get_solution
from optimization.optimization import create_and_solve_ip
from constraints.contraints_checking import check_constraint
from eval.config import Config
from const import *
from eval.discovery import dfg
from eval.measures import *
from eval.eval_result import FullResult, EvaluationResult, single_result_header, \
    full_result_header_reduced
from eval import graphpartitioning_bl, graphquerying_bl
from candidatecomputation.candidates import compute_candidate_groups
from candidatecomputation.exclusive import handle_singleton_xor_sets
from main import deserialize_event_log, prepare_single_log
from optimization.sim.simfunction import group_wise_interleaving_variants, get_groupwise_interleaving_xor
from postprocessing.create_log import create_mapping_from_groups, apply_mapping_to_log
from readwrite import load_precomputed, store_precomputed, write_xes, get_bpmn
from model.pm.dfg_util import to_real_simple_graph, get_dfg_concurrency
from pm4py.visualization.dfg import visualizer as dfg_visualization

"""
evaluation script using the synthetic logs
"""
SYNTHETIC_CAT_AM_GUARANTEE = [(XES_RESOURCE, MAX, None, 3)]
SYNTHETIC_NUM_M_GUARANTEE = [(SINCE_LAST, MIN, SUM, 60)]
SYNTHETIC_NUM_NM_GUARANTEE = [(SINCE_LAST, MAX, AVG, 5 * 100000 * 60)]
SYNTHETIC_K_GROUPS_GUARANTEE = [(NUM_GROUPS, MIN, None, 3)]

LIMIT_CONSTRAINT = (XES_NAME, MAX, None, 8)

_configs_greedy = [

    Config(efficient=False, guarantees=SYNTHETIC_CAT_AM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=True, beam_size=sys.maxsize, handle_loops=True, handle_xor=False, handle_concurrent=True,
           frac_to_hold=1),
    Config(efficient=False, guarantees=SYNTHETIC_NUM_M_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING, greedy=True,
           beam_size=sys.maxsize, handle_loops=True, handle_xor=False, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=False, guarantees=SYNTHETIC_NUM_NM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=True, beam_size=sys.maxsize, handle_loops=True, handle_xor=False, handle_concurrent=True,
           frac_to_hold=1)
]

_configs_efficient = [
    Config(efficient=True, guarantees=SYNTHETIC_CAT_AM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           frac_to_hold=1),
    Config(efficient=True, guarantees=SYNTHETIC_NUM_M_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING, greedy=False,
           beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=True, guarantees=SYNTHETIC_NUM_NM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           frac_to_hold=1),
    Config(efficient=True, guarantees=SYNTHETIC_K_GROUPS_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           frac_to_hold=1)
]

_configs_efficient_beam = [
    Config(efficient=True, guarantees=SYNTHETIC_CAT_AM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=100, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=True, guarantees=SYNTHETIC_NUM_M_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING, greedy=False,
           beam_size=100, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=True, guarantees=SYNTHETIC_NUM_NM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=100, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=True, guarantees=SYNTHETIC_K_GROUPS_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=100, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1)
]

_configs_basic = [
    Config(efficient=False, guarantees=SYNTHETIC_CAT_AM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           frac_to_hold=1),
    Config(efficient=False, guarantees=SYNTHETIC_NUM_M_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           frac_to_hold=1),
    Config(efficient=False, guarantees=SYNTHETIC_NUM_NM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           frac_to_hold=1),
    Config(efficient=False, guarantees=SYNTHETIC_K_GROUPS_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           frac_to_hold=1)
]

CAT_NUMS_MAX = [3]
CAT_NUMS_MIN = [2]
NUM_NUMS_MIN = [1 * 60]
NUM_NUMS_MAX = [1000000 * 60]
NUM_NUMS_AVG = [5 * 100000 * 60]

SPLIT_MINER_MODEL_DIR = "models/"


def run_split_miner_for_log(log_path, model_name):
    print(log_path, model_name)
    try:
        return_code = subprocess.run(["./runsm.sh", log_path, model_name], timeout=360)
    except subprocess.TimeoutExpired:
        print('process ran too long')
        return_code = 1
    return return_code


def get_synth_log_stats():
    logggs = list(get_synthetic_logs().values())
    print(len(logggs), "logs available")
    num_classes = []
    trace_lens_max = []
    trace_lens_avg = []
    trace_lens_med = []
    trace_lens_min = []
    trace_vars = []
    num_edges = []

    for log in logggs:
        print(log.name)
        num_edges.append(len(log.dfg_encoded.edges))
        num_classes.append(len(log.unique_event_classes))
        trace_lens_max.append(max([len(trace) for trace in log.traces]))
        trace_lens_avg.append(mean([len(trace) for trace in log.traces]))
        trace_lens_med.append(median([len(trace) for trace in log.traces]))
        trace_lens_min.append(min([len(trace) for trace in log.traces]))
        trace_vars.append(len(log.variants))

    print("Property & Min. & Max. & Avg. & Med. \\\\")
    print("Nodes in DFG & " + str(min(num_classes)) + "&" + str(max(num_classes)) + "&" + str(
        mean(num_classes)) + "&" + str(median(num_classes)) + "\\\\")
    print("Edges in DFG & " + str(min(num_edges)) + "&" + str(max(num_edges)) + "&" + str(mean(num_edges)) + "&" + str(
        median(num_edges)) + "\\\\")
    print("Trace variants & " + str(min(trace_vars)) + "&" + str(max(trace_vars)) + "&" + str(
        mean(trace_vars)) + "&" + str(median(trace_vars)) + "\\\\")
    print("Min. Trace length & " + str(min(trace_lens_min)) + "&" + str(max(trace_lens_min)) + "&" + str(
        mean(trace_lens_min)) + "&" + str(median(trace_lens_min)) + "\\\\")
    print("Max. Trace length & " + str(min(trace_lens_max)) + "&" + str(max(trace_lens_max)) + "&" + str(
        mean(trace_lens_max)) + "&" + str(median(trace_lens_max)) + "\\\\")
    print("Avg. Trace length & " + str(min(trace_lens_avg)) + "&" + str(max(trace_lens_avg)) + "&" + str(
        mean(trace_lens_avg)) + "&" + str(median(trace_lens_avg)) + "\\\\")
    print("Med. Trace length & " + str(min(trace_lens_med)) + "&" + str(max(trace_lens_med)) + "&" + str(
        mean(trace_lens_med)) + "&" + str(median(trace_lens_med)) + "\\\\")


def get_synthetic_logs():
    logcollection = dict()
    for (dir_path, dir_names, filenames) in os.walk(SYNTHETIC_LOGS_DIR):
        for filename in filenames:
            if ".xes" not in filename:
                continue
            event_log = deserialize_event_log(DEFAULT_LOG_SER_PATH, filename.replace(".xes", ""))
            if not event_log:
                event_log = prepare_single_log(SYNTHETIC_LOGS_DIR, filename, DEFAULT_LOG_SER_PATH)
            logcollection[filename] = event_log
            if not RUN_SPLIT_MINER:
                continue
            if not os.path.exists(SPLIT_MINER_MODEL_DIR + event_log.name + '.bpmn'):
                run_split_miner_for_log(SYNTHETIC_LOGS_DIR + event_log.name + '.xes', event_log.name)
    return logcollection


def serialize_config_result(full_result: FullResult):
    with open(os.path.join(DEFAULT_EVAL_SER_PATH, full_result.setting + "_" + str(full_result.config) + ".pkl"),
              'wb') as f:
        pickle.dump(full_result, f)


def serialize_result(result: EvaluationResult):
    with open(os.path.join(DEFAULT_EVAL_SER_PATH,
                           result.setting + "_" + str(result.config) + "_" + str(result.eval_log) + ".pkl"),
              'wb') as f:
        pickle.dump(result, f)


def deserialize_result(path, setting_to_get, conf, log):
    try:
        with open(os.path.join(path, setting_to_get + "_" + conf + "_" + log + '.pkl'), 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        print("no such file", conf, log)
        return False


def recompute_distance(groups, log):
    distance_map = {}
    print(len(groups), " to recompute the distance for")
    for group in groups:
        group_dist, co_occurrence = group_wise_interleaving_variants(group, log, handle_loops=True,
                                                                     handle_xor=True,
                                                                     handle_concurrent=True)
        if not co_occurrence:
            group_dist = get_groupwise_interleaving_xor(group, log, handle_loops=True,
                                                        handle_concurrent=True)
        distance_map[group] = group_dist
    return distance_map


def to_new(old_sr: EvaluationResult):
    new_sr = EvaluationResult(old_sr.setting, old_sr.config)
    new_sr.step1_time = old_sr.step1_time
    new_sr.step2_time = old_sr.step2_time
    new_sr.step3_time = old_sr.step3_time
    new_sr.best_solution = old_sr.best_solution
    new_sr.num_candidates = old_sr.num_candidates
    new_sr.eval_log = old_sr.eval_log
    new_sr.num_event_classes = old_sr.num_event_classes
    new_sr.num_cases = old_sr.num_cases
    new_sr.num_output_event_cases = old_sr.num_output_event_cases
    new_sr.original_log_location = old_sr.original_log_location
    new_sr.abstracted_log_location = old_sr.abstracted_log_location
    new_sr.abstracted_log_name = old_sr.abstracted_log_name
    new_sr.dfg_density_in = old_sr.dfg_density_in
    new_sr.dfg_density_out = old_sr.dfg_density_out
    new_sr.dfg_diameter_in = old_sr.dfg_diameter_in
    new_sr.dfg_diameter_out = old_sr.dfg_diameter_out
    new_sr.cfc_in = old_sr.cfc_in
    new_sr.cfc_out = old_sr.cfc_out
    new_sr.avg_conn_degree_in = old_sr.avg_conn_degree_in_bpmn
    new_sr.avg_conn_degree_out = old_sr.avg_conn_degree_out_bpmn
    new_sr.cfc_in_bpmn = old_sr.cfc_in_bpmn
    new_sr.cfc_out_bpmn = old_sr.cfc_out_bpmn
    new_sr.avg_conn_degree_in_bpmn = old_sr.avg_conn_degree_in_bpmn
    new_sr.avg_conn_degree_out_bpmn = old_sr.avg_conn_degree_out_bpmn
    new_sr.silhouette_ours = old_sr.silhouette_ours
    new_sr.silhouette_inf_dfc = old_sr.silhouette_inf_dfc
    new_sr.reached_timeout = old_sr.reached_timeout
    new_sr.reached_end_size = old_sr.reached_end_size
    new_sr.solution = old_sr.solution
    new_sr.behavioral_conf = 0
    return new_sr

def run_sp(single_result, curr_config, recompute_dist=False):
    if not os.path.exists(
          SPLIT_MINER_MODEL_DIR + single_result.abstracted_log_name + '.bpmn') or recompute_dist:
        #rc = run_split_miner_for_log(single_result.abstracted_log_location, single_result.abstracted_log_name)
        rc = run_split_miner_for_log(curr_config.abstracted_path + single_result.abstracted_log_name,
                                         single_result.abstracted_log_name)
        if rc == 1:
            return
    try:
        net_i, _, _ = get_bpmn(SPLIT_MINER_MODEL_DIR + single_result.eval_log + '.bpmn')
        net_o, _, _ = get_bpmn(SPLIT_MINER_MODEL_DIR + single_result.abstracted_log_name + '.bpmn')
        bpmn_i = get_bpmn(SPLIT_MINER_MODEL_DIR + single_result.eval_log + '.bpmn', as_petri_net=False)
        bpmn_o = get_bpmn(SPLIT_MINER_MODEL_DIR + single_result.abstracted_log_name + '.bpmn', as_petri_net=False)
        single_result.cfc_in = get_cfc(net_i)
        single_result.avg_conn_degree_in = get_acd(net_i)
        single_result.avg_conn_degree_in_bpmn = get_acd_bpmn(bpmn_i)
        single_result.cfc_in_bpmn = get_cfc_bpmn(bpmn_i)
        if single_result.num_event_classes == single_result.num_output_event_cases:
            single_result.cfc_out_bpmn = single_result.cfc_in_bpmn
            single_result.avg_conn_degree_out = single_result.avg_conn_degree_in
            single_result.avg_conn_degree_out_bpmn = single_result.avg_conn_degree_in_bpmn
            single_result.cfc_out = single_result.cfc_in
        else:
            single_result.cfc_out_bpmn = get_cfc_bpmn(bpmn_o)
            single_result.avg_conn_degree_out = get_acd(net_o)
            single_result.avg_conn_degree_out_bpmn = get_acd_bpmn(bpmn_o)
            single_result.cfc_out = get_cfc(net_o)
    except OSError:
        print("model could not be constructed before, hence we have to terminate without the simplicity scores.")
    except XMLSyntaxError:
        print("XML error")
    serialize_result(single_result)



def handle_gp(single_result, log, curr_config):
    if single_result is False:
        single_result = EvaluationResult(GP_BASELINE, curr_config)
        single_result.eval_log = log.name
        #################################################
        single_result.num_cases = log.num_cases
        single_result.num_event_classes = len(log.unique_event_classes)
        tic = time.perf_counter()
        solution_enc, solution = graphpartitioning_bl.get_candidates(log=log, guarantee=curr_config.guarantees[0])
        toc = time.perf_counter()
        single_result.step2_time = toc - tic
        single_result.solution = solution
        single_result.num_output_event_cases = len(solution)
        mapping = create_mapping_from_groups(log, solution, by_len=False)
        if curr_config.create_mapping and curr_config.do_projection:
            tic = time.perf_counter()
            pm4py_copy = deepcopy(log.pm4py)
            abstracted_log = apply_mapping_to_log(mapping, pm4py_copy,
                                                  only_complete=curr_config.only_complete)
            toc = time.perf_counter()
            i_dfg = to_real_simple_graph(log.dfg_dict, log.pm4py)
            dfgs = get_dfg_concurrency(abstracted_log)
            o_dfg = to_real_simple_graph(dfgs, abstracted_log)
            single_result.silhouette_ours = get_silhouette_for_solution(log, None, solution_enc)
            single_result.dfg_density_in = get_density(i_dfg)
            single_result.dfg_density_out = get_density(o_dfg)
            single_result.step3_time = toc - tic
            if curr_config.export_xes:
                write_xes(curr_config.abstracted_path,
                          log.name + "_" + str(curr_config).replace(":", "-") + '_abstracted',
                          abstracted_log)
                abstracted_log_name = log.name + "_" + str(curr_config).replace(":", "-") + '_abstracted.xes'
                single_result.abstracted_log_location = curr_config.abstracted_path + abstracted_log_name
                single_result.abstracted_log_name = abstracted_log_name
                single_result.original_log_location = curr_config.original_log_path + log.name + '.xes'

                serialize_result(single_result)
            else:
                serialize_result(single_result)
    if "ic19" in log.name:
        print("BPI19")
        # read input file
        fin = open(curr_config.abstracted_path + single_result.abstracted_log_name, "rt")
        # read file contents to string
        data = fin.read()
        # replace all occurrences of the required string
        data = data.replace('&', 'AND').replace(" < ", " LEQ ")
        # close the input file
        fin.close()
        # open the input file in write mode
        fin = open(curr_config.abstracted_path + single_result.abstracted_log_name, "wt")
        # overrite the input file with the resulting data
        fin.write(data)
        # close the file
        fin.close()
    if RUN_SPLIT_MINER:
        run_sp(single_result, curr_config)


def do_single_run(setting_to_run, curr_config, log, viz=False, recompute_dist=False, att_for_gq=None):
    single_result = deserialize_result(DEFAULT_EVAL_SER_PATH, setting_to_run, str(curr_config), log.name)
    if setting_to_run == GP_BASELINE:
        handle_gp(single_result, log, curr_config)
        return
    groups, dist_map = load_precomputed(log, curr_config)
    if groups is not False and single_result is not False and recompute_dist is True:
        dist_map = recompute_distance(groups, log)
    start_size, end_size, lower_k, upper_k, mode, constraint_dict = check_constraint(log, curr_config.guarantees)
    print(curr_config)
    print(constraint_dict)
    print(start_size, end_size, lower_k, upper_k, mode)
    if groups is False or single_result is False or recompute_dist:
        if single_result is False:
            single_result = EvaluationResult(setting_to_run, curr_config)
        single_result.eval_log = log.name
        #################################################
        single_result.num_cases = log.num_cases
        single_result.num_event_classes = len(log.unique_event_classes)
        if curr_config.handle_xor:
            handle_singleton_xor_sets(log)

        single_result.start_size = start_size
        single_result.end_size = end_size
        single_result.monotonicity = mode
        single_result.lower_k_requested_groups = lower_k
        single_result.upper_k_requested_groups = upper_k
        if not recompute_dist:
            tic = time.perf_counter()
            if setting_to_run == GQ_BASELINE:
                groups, dist_map = graphquerying_bl.get_candidates(log, curr_config.guarantees, att_for_gq)
                end_time = (0, 0)
            elif curr_config.greedy:
                groups, dist_map = run_greedy(log=log, constraints=curr_config.guarantees,
                                              handle_loops=curr_config.handle_loops,
                                              handle_concurrent=curr_config.handle_concurrent,
                                              frac_to_hold=curr_config.frac_to_hold)
                end_time = (0, 0)
            else:
                groups, dist_map, end_time, violation_dict = compute_candidate_groups(log, curr_config.guarantees,
                                                                      constraint_dict=constraint_dict,
                                                                      mode=mode,
                                                                      start_size=start_size, end_size=end_size,
                                                                      incl_sub_sets=(not curr_config.greedy),
                                                                      distance_notion=curr_config.distance_notion,
                                                                      beam_size=curr_config.beam_size,
                                                                      with_dfg=curr_config.efficient,
                                                                      handle_loops=curr_config.handle_loops,
                                                                      handle_xor=curr_config.handle_xor,
                                                                      handle_concurrent=curr_config.handle_concurrent,
                                                                      frac_to_hold=curr_config.frac_to_hold)
            toc = time.perf_counter()
            single_result.step1_time = toc - tic
            single_result.reached_timeout = end_time[1]
            single_result.reached_end_size = end_time[0]
            single_result.num_candidates = len(groups)

        if curr_config.store_groups:
            store_precomputed(log, curr_config, groups, dist_map)
        if len(groups) == 0:
            print("No groups found in the log for the given guarantees.\nContinuing...")
            single_result.best_solution = len(log.unique_event_classes)
            if end_time[1] != 2:
                single_result.solution = log.unique_event_classes
            single_result.num_output_event_cases = len(log.unique_event_classes)
            single_result.abstracted_log_location = curr_config.original_log_path + log.name + '.xes'
            single_result.abstracted_log_name = log.name + ".xes"
            single_result.original_log_location = curr_config.original_log_path + log.name + '.xes'
            i_dfg = to_real_simple_graph(log.dfg_dict, log.pm4py)
            single_result.dfg_density_in = get_density(i_dfg)
            single_result.dfg_density_out = single_result.dfg_density_in
            serialize_result(single_result)
            return
        if curr_config.greedy and not setting_to_run == GP_BASELINE and not setting_to_run == GQ_BASELINE:
            tic = time.perf_counter()
            solution_enc, solution, best_dist = get_solution(groups, dist_map, log)
            toc = time.perf_counter()
            single_result.step2_time = toc - tic
            single_result.best_solution = best_dist
            single_result.solution = solution
            covered = [s for sol in solution_enc for s in sol]
            if not all(s in covered for s in log.encoded_event_classes):
                print("No covering solution possible!")
                single_result.solution = []
                single_result.best_solution = len(log.unique_event_classes)
                single_result.num_output_event_cases = len(log.unique_event_classes)
                single_result.abstracted_log_location = curr_config.original_log_path + log.name + '.xes'
                single_result.abstracted_log_name = log.name + ".xes"
                single_result.original_log_location = curr_config.original_log_path + log.name + '.xes'
                i_dfg = to_real_simple_graph(log.dfg_dict, log.pm4py)
                single_result.dfg_density_in = get_density(i_dfg)
                single_result.dfg_density_out = single_result.dfg_density_in
                serialize_result(single_result)
                return
            single_result.num_output_event_cases = len(solution)
        elif curr_config.optimal_solution:
            all_covered_by_groups = list(log.encoded_event_classes)
            tic = time.perf_counter()
            solution, best_dist = create_and_solve_ip(all_covered_by_groups, len(all_covered_by_groups),
                                                      groups,
                                                      dist_map,
                                                      log,
                                                      lower_k=lower_k, upper_k=upper_k)
            try:
                solution_enc = [[log.unique_event_classes.index(i) for i in sol] for sol in solution]
            except TypeError:
                print("No covering solution possible!")
                single_result.best_solution = len(log.unique_event_classes)
                single_result.num_output_event_cases = len(log.unique_event_classes)
                single_result.abstracted_log_location = curr_config.original_log_path + log.name + '.xes'
                single_result.abstracted_log_name = log.name + ".xes"
                single_result.original_log_location = curr_config.original_log_path + log.name + '.xes'
                i_dfg = to_real_simple_graph(log.dfg_dict, log.pm4py)
                single_result.dfg_density_in = get_density(i_dfg)
                single_result.dfg_density_out = single_result.dfg_density_in
                serialize_result(single_result)
                return
            toc = time.perf_counter()
            single_result.step2_time = toc - tic
            single_result.best_solution = best_dist
            single_result.solution = solution
            single_result.num_output_event_cases = len(solution)
            if single_result.num_event_classes == single_result.num_output_event_cases:
                single_result.abstracted_log_location = curr_config.original_log_path + log.name + '.xes'
                single_result.original_log_location = curr_config.original_log_path + log.name + '.xes'
                single_result.abstracted_log_name = log.name + ".xes"
                i_dfg = to_real_simple_graph(log.dfg_dict, log.pm4py)
                single_result.dfg_density_in = get_density(i_dfg)
                single_result.dfg_density_out = single_result.dfg_density_in
                serialize_result(single_result)
                return
        if curr_config.create_mapping:
            mapping = create_mapping_from_groups(log, solution, by_len=False)
            if curr_config.do_projection:
                tic = time.perf_counter()
                pm4py_copy = deepcopy(log.pm4py)
                abstracted_log = apply_mapping_to_log(mapping, pm4py_copy,
                                                      only_complete=curr_config.only_complete)
                toc = time.perf_counter()
                i_dfg = to_real_simple_graph(log.dfg_dict, log.pm4py)
                dfgs = get_dfg_concurrency(abstracted_log)
                o_dfg = to_real_simple_graph(dfgs, abstracted_log)
                single_result.silhouette_ours = get_silhouette_for_solution(log, dist_map, solution_enc)
                single_result.silhouette_inf_dfc = get_silhouette_for_solution(log, log.dfg_dict, solution,
                                                                               inf_dfc=True)
                if viz:
                    dfg(log.pm4py, viz=True)
                    gviz = dfg_visualization.apply(dfgs, log=abstracted_log,
                                                   variant=dfg_visualization.Variants.FREQUENCY,
                                                   parameters={
                                                       dfg_visualization.frequency.Parameters.MAX_NO_EDGES_IN_DIAGRAM: 1000})
                    dfg_visualization.view(gviz)
                single_result.dfg_density_in = get_density(i_dfg)
                single_result.dfg_density_out = get_density(o_dfg)
                single_result.step3_time = toc - tic
                if curr_config.export_xes:
                    write_xes(curr_config.abstracted_path,
                              log.name + "_" + str(curr_config).replace(":", "-") + '_abstracted',
                              abstracted_log)
                    abstracted_log_name = log.name + "_" + str(curr_config).replace(":", "-") + '_abstracted.xes'
                    single_result.abstracted_log_location = curr_config.abstracted_path + abstracted_log_name
                    single_result.abstracted_log_name = abstracted_log_name
                    single_result.original_log_location = curr_config.original_log_path + log.name + '.xes'

                    serialize_result(single_result)
                else:
                    serialize_result(single_result)
    elif not hasattr(single_result, 'solution'):
        if len(groups) != 0:
            all_covered_by_groups = list(frozenset.union(*groups))
            solution, best_dist = create_and_solve_ip(all_covered_by_groups, len(all_covered_by_groups),
                                                      groups,
                                                      dist_map,
                                                      log,
                                                      lower_k=lower_k, upper_k=upper_k)
            single_result.solution = solution

        else:
            single_result.solution = log.unique_event_classes
        serialize_result(single_result)
    if "[(" in str(curr_config) or " " in  str(curr_config):
        print("renaming",  str(curr_config)+"_abstracted.xes")
        new_name = single_result.abstracted_log_name.replace("[('", "").replace("')]", "").replace("', '", "#").replace(" ","")
        try:
            os.rename(curr_config.abstracted_path + single_result.eval_log+"_" + str(curr_config)+"_abstracted.xes", curr_config.abstracted_path + new_name)
        except FileNotFoundError:
            print("already changed")
        single_result.abstracted_log_name = new_name
    if "i19" in log.name:
        print("BPI19")
        # read input file
        fin = open(curr_config.abstracted_path + single_result.abstracted_log_name, "rt")
        # read file contents to string
        data = fin.read()
        # replace all occurrences of the required string
        data = data.replace('&', 'AND').replace(" < ", " LEQ ")
        # close the input file
        fin.close()
        # open the input file in write mode
        fin = open(curr_config.abstracted_path + single_result.abstracted_log_name, "wt")
        # overrite the input file with the resulting data
        fin.write(data)
        # close the file
        fin.close()
    single_result = to_new(single_result)
    if RUN_SPLIT_MINER:
        run_sp(single_result, curr_config)


def create_all_configs(withlimit=True, efficient=True, with_beam=False, greedy=False, real=False):
    all_configs = list()
    if efficient and with_beam:
        confs = _configs_efficient_beam
    else:
        confs = _configs_efficient if efficient else _configs_basic
    if greedy:
        confs = _configs_greedy

    for cconfig in confs:

        if cconfig.guarantees[0][0] == XES_RESOURCE or cconfig.guarantees[0][0] == XES_NAME or cconfig.guarantees[0][
            0] == SINCE_LAST:
            for idx, _ in enumerate(NUM_NUMS_MIN):
                current_config = deepcopy(cconfig)
                if real:
                    current_config.original_log_path = REAL_LOGS_DIR
                if current_config.guarantees[0][0] == XES_RESOURCE or current_config.guarantees[0][0] == XES_NAME:
                    current_config.guarantees[0] = (
                        current_config.guarantees[0][0], current_config.guarantees[0][1],
                        current_config.guarantees[0][2],
                        CAT_NUMS_MIN[idx] if current_config.guarantees[0][1] == MIN else CAT_NUMS_MAX[idx])
                else:
                    if current_config.guarantees[0][2] == AVG:
                        current_config.guarantees[0] = (
                            current_config.guarantees[0][0], current_config.guarantees[0][1],
                            current_config.guarantees[0][2],
                            NUM_NUMS_AVG[idx])
                    else:
                        current_config.guarantees[0] = (
                            current_config.guarantees[0][0], current_config.guarantees[0][1],
                            current_config.guarantees[0][2],
                            NUM_NUMS_MIN[idx] if current_config.guarantees[0][1] == MIN else NUM_NUMS_MAX[idx])
                if withlimit:
                    current_config.guarantees.append(LIMIT_CONSTRAINT)
                all_configs.append(current_config)
        else:
            for idx, _ in enumerate(CAT_NUMS_MAX):

                current_config = deepcopy(cconfig)
                if real:
                    current_config.original_log_path = REAL_LOGS_DIR
                current_config.guarantees[0] = (
                    current_config.guarantees[0][0], current_config.guarantees[0][1], current_config.guarantees[0][2],
                    CAT_NUMS_MAX[idx])
                if withlimit and len(cconfig.guarantees) == 1:
                    current_config.guarantees.append(LIMIT_CONSTRAINT)
                all_configs.append(current_config)
    print(len(all_configs), "configs added")
    combi_1 = deepcopy(all_configs[0])
    if not greedy:
        combi_1.guarantees.insert(1, all_configs[2].guarantees[0])
        combi_1.guarantees.insert(1, all_configs[3].guarantees[0])

        combi_2 = deepcopy(all_configs[0])
        combi_2.guarantees.insert(1, all_configs[1].guarantees[0])
        combi_2.guarantees.insert(1, all_configs[2].guarantees[0])
        combi_2.guarantees.insert(1, all_configs[3].guarantees[0])

        all_configs.append(combi_1)
        all_configs.append(combi_2)
    return all_configs


def write_results(setting_to_write):
    results_file = RESULTS_DIR + "results_" + setting_to_write + time.strftime("%Y%m%d%H%M%S") + ".csv"
    results_time_file = RESULTS_DIR + "results_timeseries" + setting_to_write + time.strftime("%Y%m%d%H%M%S") + ".csv"
    with open(results_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        header = full_result_header_reduced
        writer.writerow(header)
        with open(results_time_file, 'w', newline='') as csvfile2:
            writer_time = csv.writer(csvfile2, delimiter=';')
            header_single = single_result_header
            writer_time.writerow(header_single)
            conf_dict = dict()
            for (dir_path, dir_names, filenames) in os.walk(DEFAULT_EVAL_SER_PATH):
                for filename in filenames:
                    if setting_to_write not in filename:
                        continue
                    else:
                        log_name = "_".join(filename.split("_")[-1:]).replace(".pkl", "")
                        config_name = "_".join(filename.split("_")[1:-1])
                        res = deserialize_result(DEFAULT_EVAL_SER_PATH, setting_to_write, config_name, log_name)
                        if not res:
                            continue
                        if config_name not in conf_dict.keys():
                            conf_dict[config_name] = []
                        conf_dict[config_name].append(res)
            for key, value in conf_dict.items():
                full_config_result = FullResult(setting_to_write, key)
                full_config_result.result_list = value
                for res in value:
                    writer_time.writerow(res.get_simple_results())
                try:
                    agg_res = full_config_result.get_aggregate_config_results_reduced(only_feasible=False)
                except AttributeError:
                    continue
                writer.writerow(agg_res)
    return results_file, results_time_file


RUN_SPLIT_MINER = False

if __name__ == "__main__":
    starttime = time.time()
    parallel = False
    setting = "ours"
    log_collection = [lo for lo in get_synthetic_logs().values()]
    print(len(log_collection), "logs")
    configs = create_all_configs(greedy=True)
    configs.extend(create_all_configs(efficient=True))
    configs.extend(create_all_configs(efficient=False))
    configs.extend(create_all_configs(efficient=True, with_beam=True))
    print(len(configs), "configs")
    combis = dict()
    for i, lg in enumerate(log_collection):
        for j, con in enumerate(configs):
            combi = (i, j)
            if combi not in combis.keys():
                if con.beam_size == 100:
                    curr_con = deepcopy(con)
                    curr_con.beam_size = 5 * len(lg.unique_event_classes)
                    con = curr_con
                combis[combi] = (con, lg)
    print(len(combis), "runs to do!")
    if parallel:
        num_workers = 1
        pool = multiprocessing.Pool(num_workers)
        for config, lg in combis.values():
            pool.apply_async(do_single_run, args=(setting, config, lg))
        pool.close()
        pool.join()
    else:
        for config, lg in combis.values():
            do_single_run(setting, config, lg, recompute_dist=False)
    write_results(setting)
    print("Evaluation on synthetic data done.")
    print('Time taken = {} seconds'.format(time.time() - starttime))
    sys.exit(0)
