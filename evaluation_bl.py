import multiprocessing
import sys
import time
from copy import deepcopy
from eval.config import Config
from const import *
from evaluation_synthetic import do_single_run, write_results, get_synthetic_logs
from evaluation_real import get_real_logs_for_quantitative_eval
from main import prepare_single_log
from model.datatype import DataType
from readwrite import replace_char_seqs_in_file

_configs_gq_bl = [
    Config(efficient=False, guarantees=[(XES_NAME, MAX, None, 5)], distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=True, beam_size=sys.maxsize, handle_loops=True, handle_xor=False, handle_concurrent=True,
           frac_to_hold=1),
    Config(efficient=False, guarantees=[(CL, [], None, 5)], distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=True, beam_size=sys.maxsize, handle_loops=True, handle_xor=False, handle_concurrent=True,
           frac_to_hold=1),
    Config(efficient=False, guarantees=[(PLACEHOLDER, EXACTLY, None, 5)], distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=True, beam_size=sys.maxsize, handle_loops=True, handle_xor=False, handle_concurrent=True,
           frac_to_hold=1)
]

_configs_gq_ours = [
    Config(efficient=True, guarantees=[(XES_NAME, MAX, None, 5)], distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=100, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=True, guarantees=[(CL, [], None, None), (XES_NAME, MAX, None, 5)],
           distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=100, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=True, guarantees=[(PLACEHOLDER, EXACTLY, None, 1), (XES_NAME, MAX, None, 5)],
           distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=100, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=True, guarantees=[(XES_NAME, MAX, None, 5)], distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=True, guarantees=[(CL, [], None, None), (XES_NAME, MAX, None, 5)],
           distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=True, guarantees=[(PLACEHOLDER, EXACTLY, None, 1), (XES_NAME, MAX, None, 5)],
           distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=False, guarantees=[(XES_NAME, MAX, None, 5)], distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=False, guarantees=[(CL, [], None, None), (XES_NAME, MAX, None, 5)],
           distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=False, guarantees=[(PLACEHOLDER, EXACTLY, None, 1), (XES_NAME, MAX, None, 5)],
           distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1)
]

_configs_gp_bl = [
    Config(efficient=False, guarantees=[(NUM_GROUPS, EXACTLY, None, 5)], distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=True, beam_size=sys.maxsize, handle_loops=True, handle_xor=False, handle_concurrent=True,
           frac_to_hold=1),
]

_configs_gp_ours = [
    Config(efficient=True, guarantees=[(NUM_GROUPS, MIN, None, 5), (NUM_GROUPS, MAX, None, 5)], distance_notion=INTER_GROUP_INTERLEAVING,
             greedy=False, beam_size=100, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=True, guarantees=[(NUM_GROUPS, MIN, None, 5), (NUM_GROUPS, MAX, None, 5)], distance_notion=INTER_GROUP_INTERLEAVING,
            greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1),
    Config(efficient=False, guarantees=[(NUM_GROUPS, MIN, None, 5), (NUM_GROUPS, MAX, None, 5)], distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True, frac_to_hold=1)
]


def run_baselines():
    setting = GP_BASELINE
    for name, log in log_collection.items():
        for config in _configs_gp_bl:
            config_copy = deepcopy(config)
            config_copy.guarantees[0] = (
                config.guarantees[0][0], config.guarantees[0][1], None, int(len(log.unique_event_classes) / 2))
            do_single_run(setting, config_copy, log, recompute_dist=False)
    write_results(setting)
    avg_file, full_details = write_results(setting)
    replace_char_seqs_in_file(avg_file, ["org-group"], ["org-resource"])
    replace_char_seqs_in_file(full_details, ["org-group"], ["org-resource"])
    setting = GQ_BASELINE
    cls = {}
    for name, log in log_collection.items():
        left = log.unique_event_classes[int(len(log.unique_event_classes) / 2)]
        right = log.unique_event_classes[int(len(log.unique_event_classes) / 4)]
        rand_cl_guarantee = (left, right)
        cls[log.name] = rand_cl_guarantee
        for config in _configs_gq_bl:
            if config.guarantees[0][0] == CL:
                config_copy = deepcopy(config)
                config_copy.guarantees[0] = (CL, [rand_cl_guarantee], None, config.guarantees[0][3])
                do_single_run(setting, config_copy, log, recompute_dist=False)
            elif config.guarantees[0][0] == PLACEHOLDER:
                for att in log.event_att_to_type.keys():
                    if att != XES_NAME and att != XES_LIFECYCLE and "case" not in att and log.event_att_to_type[
                        att] == DataType.CAT and all(
                        len(log.get_att_vals_for_ec[ec][att]) < 2 for ec in log.unique_event_classes):
                        config_copy = deepcopy(config)
                        print(att + " can be handled on the class-level")
                        config_copy.guarantees[0] = (
                            att, config.guarantees[0][1], config.guarantees[0][2], config.guarantees[0][3])
                        do_single_run(setting, config_copy, log, recompute_dist=False, att_for_gq=att)
                        break
            else:
                do_single_run(setting, config, log, recompute_dist=False)
    write_results(setting)
    avg_file, full_details = write_results(setting)
    replace_char_seqs_in_file(avg_file, ["org-group"], ["org-resource"])
    replace_char_seqs_in_file(full_details, ["org-group"], ["org-resource"])


def run_ours():
    parallel = False
    setting = "ours"
    cls = {}
    combis = set()
    for name, log in log_collection.items():
        left = log.unique_event_classes[int(len(log.unique_event_classes) / 2)]
        right = log.unique_event_classes[int(len(log.unique_event_classes) / 4)]
        rand_cl_guarantee = (left, right)
        cls[log.name] = rand_cl_guarantee
        for config in _configs_gq_ours:
            if config.guarantees[0][0] == CL:
                config_copy = deepcopy(config)
                config_copy.guarantees[0] = (CL, [cls[log.name]], None, config.guarantees[0][3])
                combis.add((config_copy, log))
            elif config.guarantees[0][0] == PLACEHOLDER:
                for att in log.event_att_to_type.keys():
                    if att != XES_NAME and att != XES_LIFECYCLE and "case" not in att and log.event_att_to_type[
                        att] == DataType.CAT and all(
                        len(log.get_att_vals_for_ec[ec][att]) < 2 for ec in log.unique_event_classes):
                        config_copy = deepcopy(config)
                        config_copy.guarantees[0] = (
                            att, config_copy.guarantees[0][1], config_copy.guarantees[0][2],
                            config_copy.guarantees[0][3])
                        combis.add((config_copy, log))
                        break
            else:
                combis.add((config, log))
        for config in _configs_gp_ours:
            config_copy = deepcopy(config)
            config_copy.guarantees[0] = (
                config.guarantees[0][0], config.guarantees[0][1], None, int(len(log.unique_event_classes) / 2))
            config_copy.guarantees[1] = (
                config.guarantees[1][0], config.guarantees[1][1], None, int(len(log.unique_event_classes) / 2)+1)
            combis.add((config_copy, log))
    if parallel:
        num_workers = 1
        pool = multiprocessing.Pool(num_workers)
        for config, lg in combis:
            if config.beam_size == 100:
                curr_con = deepcopy(config)
                curr_con.beam_size = 5 * len(lg.unique_event_classes)
                config = curr_con
            pool.apply_async(do_single_run, args=(setting, config, lg))
        pool.close()
        pool.join()
    else:
        for config, lg in combis:
            if config.beam_size == 100:
                curr_con = deepcopy(config)
                curr_con.beam_size = 5 * len(lg.unique_event_classes)
                config = curr_con
            do_single_run(setting, config, lg, recompute_dist=False)
    write_results(setting)
    avg_file, full_details = write_results(setting)
    replace_char_seqs_in_file(avg_file, ["org-group"], ["org-resource"])
    replace_char_seqs_in_file(full_details, ["org-group"], ["org-resource"])


if __name__ == "__main__":
    starttime = time.time()
    #log_collection = get_synthetic_logs() # UNCOMMENT FOR SYNTHETIC LOGS
    log_collection = get_real_logs_for_quantitative_eval()
    run_baselines()
    run_ours()
    print("Evaluation on baselines done.")
    print('Time taken = {} seconds'.format(time.time() - starttime))
    sys.exit(0)
