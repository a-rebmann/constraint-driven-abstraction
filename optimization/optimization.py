import gurobipy as gp
from gurobipy import GRB


def create_and_solve_ip(all_classes, num_classes, groups, dist, event_log, lower_k=None, upper_k=None):
    m = gp.Model("Optimal exact cover")
    select = m.addVars(range(len(groups)), vtype=GRB.BINARY, name='select')
    covered = m.addVars(all_classes, vtype=GRB.BINARY, name='covered')
    obj = gp.quicksum(dist[groups[i]] * select[i] for i in range(len(groups)))
    m.setObjective(obj, GRB.MINIMIZE)
    if upper_k is not None and lower_k is not None:
        if upper_k == lower_k:
            m.addConstr(select.sum() == upper_k, name="class limit")
        else:
            m.addConstr(select.sum() <= upper_k, name="class limit")
            m.addConstr(select.sum() >= lower_k, name="class limit")
    else:
        pass
       #m.addConstr(select.sum() <= num_classes, name="class limit")
    m.addConstr(covered.sum() == num_classes, name="class coverage")
    m.addConstrs((gp.quicksum(select[t] for t in range(len(groups)) if r in groups[t]) == 1#covered[r]
                  for r in all_classes), name="exact cover")
    # Find the optimal solution
    m.optimize()
    try:
        solution = [map_to_classes(groups[i], event_log) for i in select.keys() if abs(select[i].x) > 1e-6]
        obj_val = m.objVal
    except AttributeError:
        print("No solution was found for the given constraints!")
        solution = all_classes
        obj_val = len(all_classes)
    print(solution)
    return solution, obj_val


def map_to_classes(sol_group, log):
    return [log.unique_event_classes[i] for i in sol_group]