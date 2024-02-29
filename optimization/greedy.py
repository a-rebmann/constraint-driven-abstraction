import numpy as np
from optimization.sim.simmatrix import convert_to_full_matrix


def create_ranking(log, groups, distance_map):
    unique_classes = log.unique_event_classes
    num_classes = len(unique_classes)
    matrix = np.empty((num_classes * (num_classes - 1)) // 2, dtype=np.double)
    counter = 0
    for i in range(num_classes - 1):
        for j in range(i + 1, num_classes):
            curr = frozenset([i, j])
            if curr in distance_map.keys():
                matrix[counter] = distance_map[curr]
            else:
                matrix[counter] = 1
            counter += 1
    matrix = convert_to_full_matrix(matrix, False)
    group_to_sim = {}
    for group in groups:
        sim = 0
        for i in group:
            for j in group:
                sim += matrix[i][j]
        group_to_sim[frozenset(group)] = sim
    return group_to_sim