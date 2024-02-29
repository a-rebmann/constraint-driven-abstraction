import sys

from sklearn.cluster import SpectralClustering
import numpy as np

from eval.greedy_bl import map_to_classes
from const import NUM_GROUPS, XES_RESOURCE, EXACTLY, IN_PATH, INTER_GROUP_INTERLEAVING
from eval.config import Config
from main import prepare_single_log
from readwrite import deserialize_event_log


def get_candidates(log, guarantee):
    if guarantee[0] != NUM_GROUPS and guarantee[1] != EXACTLY:
        print("Graph partitioning can only handle grouping constraints with an exact number of groups.")
        return list(log.unique_event_classes)
    res = do_spectral(log, guarantee[3])
    sol_dict = {}
    for i, cls in enumerate(log.encoded_event_classes):
        if res[i] not in sol_dict.keys():
            sol_dict[res[i]] = [cls]
        else:
            sol_dict[res[i]].append(cls)
    solution_enc = [group for group in sol_dict.values()]
    solution = [map_to_classes(sol, log) for sol in solution_enc]
    print(solution)
    return solution_enc, solution


def do_spectral(log, k):
    matrix = np.empty((len(log.unique_event_classes), len(log.unique_event_classes)), dtype=np.double)
    for i in range(len(log.unique_event_classes)):
        for j in range(len(log.unique_event_classes)):
            if i == j:
                matrix[i, j] = 0
                continue
            # if (log.unique_event_classes[i], log.unique_event_classes[j]) in log.behavioral_profile["exclusive"]:
            #     right = log.activity_counts[log.unique_event_classes[i]]
            #     left = log.activity_counts[log.unique_event_classes[j]]
            # else:
            right = log.dfg_dict[(log.unique_event_classes[i], log.unique_event_classes[j])] if (log.unique_event_classes[i], log.unique_event_classes[j]) in log.dfg_dict.keys() else 0
            left = log.dfg_dict[(log.unique_event_classes[j], log.unique_event_classes[i])] if (log.unique_event_classes[j], log.unique_event_classes[i]) in log.dfg_dict.keys() else 0
            curr_dist = 1 - (1 / (right + left + 1))
            matrix[i, j] = curr_dist
    return spectral(matrix, k)


def spectral(dist_matrix, num_clust):
    clustering = SpectralClustering(n_clusters=num_clust, affinity="precomputed", assign_labels="discretize", random_state=0).fit(dist_matrix)
    return clustering.labels_


RUNNING_EXAMPLE_CONSTRAINT = [(XES_RESOURCE, EXACTLY, None, 1)]

CONFIG = Config(efficient=True, guarantees=RUNNING_EXAMPLE_CONSTRAINT, distance_notion=INTER_GROUP_INTERLEAVING,
                greedy=False,
                optimal_solution=True,
                create_mapping=True, do_projection=True, only_complete=False, xes=True, handle_xor=True,
                handle_loops=True, handle_concurrent=True)

if __name__ == "__main__":
    event_log = deserialize_event_log("../" + CONFIG.log_ser_path, "runningexample")
    if not event_log:
        event_log = prepare_single_log("../" + IN_PATH, "runningexample.xes", "../" + CONFIG.log_ser_path)
    get_candidates(event_log, (NUM_GROUPS, EXACTLY, 0, 3))
    sys.exit(0)