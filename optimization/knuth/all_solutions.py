import numpy as np
import optimization.knuth.e_cover as ec

from model.pm.log import Log


def compute_all_valid_solutions(groups, event_classes, k=None):
    matrix = []
    for group in groups:
        matrix.append([1 if elm in group else 0 for elm in event_classes])
    return get_exact_covers(matrix, event_classes, k)


def get_exact_covers(matrix, event_lasses, k=None):
    exact_cover = ec.ExactCover(matrix)
    solutions = exact_cover.get_all_solutions()
    if k is not None:
        solutions = [sol for sol in solutions if len(sol) <= k]
    else:
        smallest_k = len(event_lasses)
        lens = []
        for i, sol in enumerate(solutions):
            if len(sol) < smallest_k:
                lens.clear()
                lens.append(i)
                smallest_k = len(sol)
            elif len(sol) == smallest_k:
                lens.append(i)
        print("possible solutions " + str(len(lens)) + " with k <=" + str(smallest_k))
        solutions = solutions[lens]
    return np.array(matrix), solutions


def sim_of_group(group, dist):
    if len(group) <= 1:
        return 0
    sim = 0
    cnt = 0
    for i in group:
        for j in group:
            if i == j:
                continue
            sim += dist[i][j]
            cnt += 1
    return sim/cnt


def sim_of_group_min(group, dist):
    if len(group) <= 1:
        return 0
    sims = []
    for i in group:
        for j in group:
            if i == j:
                continue
            sims.append(dist[i][j])
    return min(sims)


def compute_group_wise_similarity(groups, event_classes, dist):
    known_values = {}
    for group in groups:
        if frozenset(group) not in known_values.keys():
            known_values[frozenset(group)] = sim_of_group(group, dist)
    for i in event_classes:
        if frozenset([i]) in known_values.keys():
            known_values[frozenset([i])] = 0
        for j in event_classes:
            if not i == j or frozenset([i, j]) in known_values.keys():
                known_values[frozenset([i, j])] = dist[i][j]
    return known_values


def find_best_solution(matrix, dist, possible_solutions, event_classes, event_log: Log):
    if len(possible_solutions) == 0:
        print("There is no solution possible")
        return []
    print(len(possible_solutions), " solutions possible.")
    global_sim = {}

    known_values = {}
    for i in range(len(event_classes)):
        if frozenset([i]) in known_values.keys():
            known_values[frozenset([i])] = 0
        for j in range(len(event_classes)):
            if not i == j or frozenset([i, j]) in known_values.keys():
                known_values[frozenset([i, j])] = dist[i][j]
    for num_of_sol, solution in enumerate(possible_solutions):
        solution_set = matrix[solution]
        # print(solution_set)
        solution_set = [[i for i in range(len(s)) if s[i] == 1] for s in solution_set]
        # print(solution_set)
        sum_of_sim = 0
        for group in solution_set:
            if frozenset(group) not in known_values.keys():
                known_values[frozenset(group)] = sim_of_group(group, dist)
            sum_of_sim += known_values[frozenset(group)]
        global_sim[num_of_sol] = sum_of_sim
    ranking = dict(sorted(global_sim.items(), key=lambda item: item[1], reverse=True))
    num_of_best = next(iter(ranking))
    best_solution = possible_solutions[num_of_best]
    sets_of_best_solution = matrix[best_solution]
    sol_groups = [map_to_classes(sol_group, event_classes, event_log) for sol_group in sets_of_best_solution]
    print(sol_groups, ranking[num_of_best])
    return sol_groups


def find_best_solution_with_group_wise_sim(matrix, dist_map, possible_solutions, event_classes, event_log: Log):
    if len(possible_solutions) == 0:
        print("There is no solution possible")
        return []
    print(len(possible_solutions), " solutions possible.")
    global_sim = {}

    for num_of_sol, solution in enumerate(possible_solutions):
        solution_set = matrix[solution]
        solution_set = [[event_classes[i] for i in range(len(s)) if s[i] == 1] for s in solution_set]
        # print(solution_set)
        global_sim[num_of_sol] = sum(dist_map[frozenset(sol)] for sol in solution_set)
    ranking = dict(sorted(global_sim.items(), key=lambda item: item[1]))
    num_of_best = next(iter(ranking))
    best_solution = possible_solutions[num_of_best]
    sets_of_best_solution = matrix[best_solution]
    sol_groups = [map_to_classes(sol_group, event_classes, event_log) for sol_group in sets_of_best_solution]
    print(sol_groups, ranking[num_of_best])
    return sol_groups


def find_best_solution_with_metric(matrix, dist, possible_solutions, event_classes, event_log: Log):
    if len(possible_solutions) == 0:
        print("There is no solution possible")
        return []
    print(len(possible_solutions), " solutions possible.")
    global_sim = {}

    for num_of_sol, solution in enumerate(possible_solutions):
        solution_set = matrix[solution]
        solution_set = [[event_classes[i] for i in range(len(s)) if s[i] == 1] for s in solution_set]
        # print(solution_set)
        global_sim[num_of_sol] = get_silhouette_for_solution(solution_set, dist)
    ranking = dict(sorted(global_sim.items(), key=lambda item: item[1], reverse=True))
    num_of_best = next(iter(ranking))
    best_solution = possible_solutions[num_of_best]
    sets_of_best_solution = matrix[best_solution]
    sol_groups = [map_to_classes(sol_group, event_classes, event_log) for sol_group in sets_of_best_solution]
    print(sol_groups, ranking[num_of_best])
    return sol_groups


def map_to_classes(sol_group, event_classes, log):
    solution_set = [event_classes[i] for i in range(len(sol_group)) if sol_group[i] == 1]
    return [log.unique_event_classes[i] for i in solution_set]


def get_silhouette_for_solution(solution, dist):
    from sklearn.metrics import silhouette_score
    idx_to_label = {}
    labels = []
    for i, sol in enumerate(solution):
        for idx in sol:
            idx_to_label[idx] = i
    for i in range(len(dist)):
        if i not in idx_to_label.keys():
            labels.append(i+len(solution)-1)
        else:
            labels.append(idx_to_label[i])
    score = silhouette_score(dist, labels, metric='precomputed')
    return score

