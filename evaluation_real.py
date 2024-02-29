import multiprocessing
import os
import sys
import time
from copy import deepcopy
from statistics import mean, median

from eval.config import Config
from const import *
from evaluation_synthetic import do_single_run, write_results, RUN_SPLIT_MINER, SPLIT_MINER_MODEL_DIR, \
    run_split_miner_for_log
from evaluation_synthetic import create_all_configs as quantitative_configs
from main import prepare_single_log
from readwrite import deserialize_event_log, replace_char_seqs_in_file

real_logs_for_quantitative_eval = [
    "bpic17c", "bpi20p", "bpic13", "bpi19h", "rtfm", "sepsis", "wabo", "bpic12", "ccc19",
    "credit", "bpic14", "bpi151f", "bpi18y"
]

real_logs_to_categorical = {
    "sepsis.xes": "org:group"
}

# CONSTRAINT FOR CASE STUDY
CONSTRAINTS = {
    "bpic17c": [
        [("EventOrigin", MAX, None, 1)],
    ]
}


def get_real_logs_for_quantitative_eval():
    log_collection = dict()
    for (dir_path, dir_names, filenames) in os.walk(REAL_LOGS_DIR):
        for filename in filenames:
            if (".xes" not in filename and ".csv" not in filename) or (
                    filename.replace(".xes", "") not in real_logs_for_quantitative_eval and filename.replace(".csv",
                                                                                                             "") not in real_logs_for_quantitative_eval):
                continue
            event_log = deserialize_event_log(DEFAULT_LOG_SER_PATH, filename.replace(".xes", "").replace(".csv", ""))
            if not event_log:
                event_log = prepare_single_log(REAL_LOGS_DIR, filename, DEFAULT_LOG_SER_PATH)
            log_collection[filename] = event_log
            if not RUN_SPLIT_MINER:
                continue
            if (not os.path.exists(SPLIT_MINER_MODEL_DIR + event_log.name + '.bpmn')):
                run_split_miner_for_log(REAL_LOGS_DIR + event_log.name + '.xes', event_log.name)
    return log_collection


def get_real_logs():
    log_collection = dict()
    for (dir_path, dir_names, filenames) in os.walk(REAL_LOGS_DIR):
        for filename in filenames:
            if (".xes" not in filename and ".csv" not in filename) or (
                    filename.replace(".xes", "") not in CONSTRAINTS.keys() and filename.replace(".csv",
                                                                                                "") not in CONSTRAINTS.keys()):
                continue
            event_log = deserialize_event_log(DEFAULT_LOG_SER_PATH, filename.replace(".xes", "").replace(".csv", ""))
            if not event_log:
                event_log = prepare_single_log(REAL_LOGS_DIR, filename, DEFAULT_LOG_SER_PATH)
            log_collection[filename] = event_log
            if not RUN_SPLIT_MINER:
                continue
            if (not os.path.exists(SPLIT_MINER_MODEL_DIR + event_log.name + '.bpmn')):
                run_split_miner_for_log(REAL_LOGS_DIR + event_log.name + '.xes', event_log.name)
    return log_collection


def create_all_configs(logs):
    real_configs = dict()
    i = 1
    for key in logs.keys():
        constraints_for_log = CONSTRAINTS[key.replace(".xes", "").replace(".csv", "")]
        for constraint in constraints_for_log:
            conf = Config(efficient=True, guarantees=constraint, distance_notion=INTER_GROUP_INTERLEAVING,
                          greedy=False, beam_size=1000, handle_loops=True, handle_xor=True, handle_concurrent=True,
                          original_log_path=REAL_LOGS_DIR, only_complete=False)
            real_configs[i] = (conf, logs[key])
            i += 1
    return real_configs


def get_log_stats():
    logggs = list(get_real_logs_for_quantitative_eval().items())
    print(len(logggs), "logs available")
    num_classes = []
    trace_lens_max = []
    trace_lens_avg = []
    trace_lens_med = []
    trace_lens_min = []
    trace_vars = []
    num_edges = []

    for nam, lag in get_real_logs_for_quantitative_eval().items():
        print(lag.name + "&" + str(len(lag.cases)) + "&" + str(len(lag.dfg_encoded.edges)) + "&" + str(
            len(lag.unique_event_classes)) + "&" + str(len(lag.variants)) + "&" + str(
            max([len(trace) for trace in lag.traces])) + "&" + str(
            min([len(trace) for trace in lag.traces])) + "&" + str(
            mean([len(trace) for trace in lag.traces])) + "&" + str(median([len(trace) for trace in lag.traces])))
        num_edges.append(len(lag.dfg_encoded.edges))
        num_classes.append(len(lag.unique_event_classes))
        trace_lens_max.append(max([len(trace) for trace in lag.traces]))
        trace_lens_avg.append(mean([len(trace) for trace in lag.traces]))
        trace_lens_med.append(median([len(trace) for trace in lag.traces]))
        trace_lens_min.append(min([len(trace) for trace in lag.traces]))
        trace_vars.append(len(lag.variants))
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


RUN_QUANTITATIVE = True  # SET TO False for Case Study
ADAPT_CONSTRAINTS_TO_LOG = False

if __name__ == "__main__":
    if RUN_QUANTITATIVE:
        starttime = time.time()
        parallel = False
        setting = "ours"
        log_collection = get_real_logs_for_quantitative_eval()
        print(len(log_collection), "logs")
        configs = quantitative_configs(greedy=True, real=True)
        configs.extend(quantitative_configs(efficient=True, with_beam=True, real=True))
        configs.extend(quantitative_configs(efficient=True, real=True))
        configs.extend(quantitative_configs(efficient=False, real=True))
        print(len(configs), "configs")
        combis = dict()
        for i, lg in enumerate(log_collection.keys()):
            for j, con in enumerate(configs):
                combi = (i, j)
                if lg in real_logs_to_categorical.keys() and con.guarantees[0][0] == XES_RESOURCE:
                    curr_con = deepcopy(con)
                    curr_con.guarantees[0] = (
                        real_logs_to_categorical[lg], curr_con.guarantees[0][1],
                        curr_con.guarantees[0][2], curr_con.guarantees[0][3])
                    con = curr_con

                if con.beam_size == 100:
                    curr_con = deepcopy(con)
                    curr_con.beam_size = 5 * len(log_collection[lg].unique_event_classes)
                    con = curr_con

                if ADAPT_CONSTRAINTS_TO_LOG:
                    guarantees = []
                    for guarantee in con.guarantees:
                        if guarantee[0] == XES_RESOURCE or guarantee[0] in real_logs_to_categorical.values():
                            num_cat = int(log_collection[lg].get_med_num_unique_per_case(guarantee[0]) / 3)
                            g_new = (guarantee[0], guarantee[1], guarantees[2], num_cat)
                            guarantees.append(g_new)
                        elif guarantee[0] == SINCE_LAST:
                            num = log_collection[lg].get_mean_case_dur() / 6
                            g_new = (guarantee[0], guarantee[1], guarantees[2], num)
                            guarantees.append(g_new)
                        else:
                            guarantees.append(guarantee)
                    con.guarantees = guarantees
                if combi not in combis.keys():
                    combis[combi] = (con, log_collection[lg])
        print(len(combis), "runs to do!")
        # sys.exit(0)
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
        avg_file, full_details = write_results(setting)
        replace_char_seqs_in_file(avg_file, ["org-group"], ["org-resource"])
        replace_char_seqs_in_file(full_details, ["org-group"], ["org-resource"])
        print("Evaluation on synthetic data done.")
        print('Time taken = {} seconds'.format(time.time() - starttime))
        sys.exit(0)
    else:
        starttime = time.time()
        parallel = False
        setting = "real"
        log_collection = get_real_logs()
        print(len(log_collection), "logs")
        combis = create_all_configs(log_collection)
        print(len(combis), "runs to do!")
        if parallel:
            num_workers = 1

            pool = multiprocessing.Pool(num_workers)
            for config, log in combis.values():
                print(config, log.name)
                pool.apply_async(do_single_run, args=(setting, config, log))
            pool.close()
            pool.join()
        else:
            for config, log in combis.values():
                do_single_run(setting, config, log, viz=False)
        write_results(setting)
        print("Evaluation on real data done.")
        print('Time taken = {} seconds'.format(time.time() - starttime))
        sys.exit(0)
