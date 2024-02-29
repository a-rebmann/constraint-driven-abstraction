from const import *
from model.datatype import DataType
from model.pm.log import Log


def check_constraint(log: Log, constraints):
    """
    Constraints are of shape (attribute | bound | aggregation function | target value)
    We determine the configuration of the group mining depending on the constraints that need to be satisfied
    """
    const_dict = {GROUPING: [], CLASS_BASED: [], INSTANCE_BASED: []}
    start_size = 2
    end_size = len(log.unique_event_classes)
    upper_k = len(log.unique_event_classes) - 1
    lower_k = 1
    modes = []
    for idx, constraint in enumerate(constraints):
        if constraint[0] == NUM_GROUPS:
            const_dict[GROUPING].append(constraint)
            if constraint[1] == MAX:
                upper_k = constraint[3]
            elif constraint[1] == MIN:
                lower_k = constraint[3]
            elif constraint[1] == EXACTLY:
                lower_k = constraint[3]
                upper_k = constraint[3]
            continue
        # first check whether we have a valid attribute for the constraint
        elif constraint[0] not in log.event_att_to_type:
            continue
        ################################################################################################################
        # the below is for constraints to handle the number of event classes, i.e. the attribute is the event label
        if constraint[0] == log.event_label:
            const_dict[CLASS_BASED].append(constraint)
            if constraint[1] == EXACTLY:
                # if the target value is larger than 2 we can simply start with larger candidates
                if constraint[3] > start_size:
                    start_size = constraint[3]
                end_size = start_size + 1
                # break
            elif constraint[1] == MAX:
                # if the target value is larger than 2 we can simply end with the max size
                if constraint[3] <= end_size:
                    end_size = constraint[3] + 1
            elif constraint[1] == MIN:
                if constraint[3] > start_size:
                    start_size = constraint[3]
        elif constraint[0] == CL:
            const_dict[CLASS_BASED].append(constraint)
            modes.append(ANTI_MONO)
        elif constraint[0] == ML:
            const_dict[CLASS_BASED].append(constraint)
            modes.append(NON_MONO)
        ################################################################################################################
        # The below are categorical attributes, there is one exception which is the event class itself (handled above)
        elif log.event_att_to_type[constraint[0]] == DataType.CAT:
            if all(len(log.get_att_vals_for_ec[ec][constraint[0]]) < 2 for ec in log.unique_event_classes):
                const_dict[CLASS_BASED].append(constraint)
            else:
                const_dict[INSTANCE_BASED].append(constraint)
            if constraint[1] == EXACTLY:
                # if the target value is larger than 2 we can simply start with larger candidates
                if constraint[3] > start_size:
                    start_size = constraint[3]
                modes.append(ANTI_MONO)
                # break
            elif constraint[1] == MAX:
                modes.append(ANTI_MONO)
            elif constraint[1] == MIN:
                # there is one attribute value per event so we can safely start at the min num required for computation
                if constraint[3] > start_size:
                    start_size = constraint[3]
                modes.append(MONO)
        ################################################################################################################
        # The below are numeric attributes including duration and positions in a trace
        elif log.event_att_to_type[constraint[0]] == DataType.NUM:
            const_dict[INSTANCE_BASED].append(constraint)
            if constraint[1] == EXACTLY:
                if constraint[2] == SUM:
                    modes.append(NON_MONO)
            elif constraint[1] == MAX:
                if constraint[2] == SUM:
                    modes.append(ANTI_MONO)
                elif constraint[2] == AVG:
                    modes.append(NON_MONO)
            elif constraint[1] == MIN:
                if constraint[2] == SUM:
                    modes.append(MONO)

        ###############
        # MAX_GAP is implemented
        elif constraint[1] == GAP:
            modes.append(ANTI_MONO)
        if len(constraints) == 1 and constraint[0] == log.event_label and constraint[1] == MAX:
            modes.append(ANTI_MONO)
            end_size = constraint[3] + 1

    if all([m == MONO for m in modes]):
        mode = MONO
    elif any([m == ANTI_MONO for m in modes]):
        mode = ANTI_MONO
    else:
        mode = NON_MONO
    return start_size, end_size, lower_k, upper_k, mode, const_dict


def check_categorical(log, case, violation_dict, index, att, event_set, mode, num):
    if mode == EXACTLY:
        res = len(
            set.union(*[set(case.get_att_for_label(log.unique_event_classes[e], att)) for e in event_set])) == num
        if not res:
            violation_dict[event_set][1][index] += 1
        return res
    elif mode == MAX:
        res = len(
            set.union(*[set(case.get_att_for_label(log.unique_event_classes[e], att)) for e in event_set])) <= num
        if not res:
            violation_dict[event_set][1][index] += 1
        return res
    elif mode == MIN:
        res = len(
            set.union(*[set(case.get_att_for_label(log.unique_event_classes[e], att)) for e in event_set])) >= num
        if not res:
            violation_dict[event_set][1][index] += 1
        return res
    else:
        return True


def check_numerical(log, case, violation_dict, index, att, event_set, mode, agg_func, num):
    if mode == EXACTLY:
        if agg_func == SUM:
            res = sum([x for e in event_set for x in case.get_att_for_label(log.unique_event_classes[e], att)]) == num
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
        elif agg_func == AVG:
            s = [x for e in event_set for x in case.get_att_for_label(log.unique_event_classes[e], att)]

            if len(s) == 0:
                print("no attribute in set", att, event_set)
                return True
            res = sum(s) / len(s) == num
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
    elif mode == MAX:
        if agg_func == SUM:
            s = [x for e in event_set for x in case.get_att_for_label(log.unique_event_classes[e], att)]
            res = sum(s) <= num
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
        elif agg_func == AVG:
            s = [x for e in event_set for x in case.get_att_for_label(log.unique_event_classes[e], att)]
            if len(s) == 0:
                print("no attribute in set", att, event_set)
                return True
            res = sum(s) / len(s) <= num
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
    elif mode == MIN:
        s = [x for e in event_set for x in case.get_att_for_label(log.unique_event_classes[e], att)]
        if agg_func == SUM:
            res = sum(s) >= num or (len(s) <= 1 and sum(s) == 0)
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
        elif agg_func == AVG:

            if len(s) == 0:
                print("no attribute in set", att, event_set)
                return True
            res = sum(s) / len(s) >= num
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
    # for the span constraint agg_func is the lower, num the upper
    elif mode == SPAN:
        nums = [x for e in event_set for x in case.get_att_for_label(log.unique_event_classes[e], att)]
        res = agg_func <= max(nums) - min(nums) <= num
        if not res:
            violation_dict[event_set][1][index] += 1
        return res
    elif mode == GAP:
        # times = [case.events[i].timestamp for i, lab in enumerate(case.events) if log.unique_event_classes.index(lab.label) in event_set]
        poses = [i for i, lab in enumerate(case.events) if log.unique_event_classes.index(lab.label) in event_set]
        if len(poses) < 2:
            return True
        # first = min(poses)
        # last = max(poses)
        # if att == POS:
        #     if last - first > num:
        #         return False
        # elif att == XES_TIME:
        #     first = min(times)
        #     last = max(times)
        #     if (last - first).total_seconds() > num:
        #         return False
        # else:
        #     if case.events[last].attributes[att] - case.events[first].attributes[att] > num:
        #         return False
        prev = None
        for i, curr in enumerate(poses):
            if i != 0:
                if att == POS:
                    if curr - prev > num:
                        return False
                elif att == XES_TIME:
                    if (case.events[curr].timestamp - case.events[prev].timestamp).total_seconds() > num:
                        return False
                else:
                    if case.events[curr].attributes[att] - case.events[prev].attributes[att] > num:
                        return False
            prev = curr
        return True
    else:
        return True


def check_categorical_with_label(case, violation_dict, index, att, event_set, mode, num):
    if mode == EXACTLY:
        res = len(
            set.union(*[set(case.get_att_for_label(e, att)) for e in event_set])) == num
        if not res:
            violation_dict[event_set][1][index] += 1
        return res
    elif mode == MAX:
        res = len(
            set.union(*[set(case.get_att_for_label(e, att)) for e in event_set])) <= num
        if not res:
            violation_dict[event_set][1][index] += 1
        return res
    elif mode == MIN:
        res = len(
            set.union(*[set(case.get_att_for_label(e, att)) for e in event_set])) >= num
        if not res:
            violation_dict[event_set][1][index] += 1
        return res
    else:
        return True


def check_numerical_with_label(case, violation_dict, index, att, event_set, mode, agg_func, num):
    if mode == EXACTLY:
        if agg_func == SUM:
            res = sum([x for e in event_set for x in case.get_att_for_label(e, att)]) == num
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
        elif agg_func == AVG:
            s = [x for e in event_set for x in case.get_att_for_label(e, att)]
            if len(s) == 0:
                print("no attribute in set", att, event_set)
                return True
            res = sum(s) / len(s) == num
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
    elif mode == MAX:
        if agg_func == SUM:
            res = sum([x for e in event_set for x in case.get_att_for_label(e, att)]) <= num
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
        elif agg_func == AVG:
            s = [x for e in event_set for x in case.get_att_for_label(e, att)]
            if len(s) == 0:
                print("no attribute in set WL", att, event_set)
                return True
            res = sum(s) / len(s) <= num
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
    elif mode == MIN:
        if agg_func == SUM:
            res = sum([x for e in event_set for x in case.get_att_for_label(e, att)]) >= num
            if not res:
                violation_dict[event_set][1][index] += 1
            return res
        elif agg_func == AVG:
            s = [x for e in event_set for x in case.get_att_for_label(e, att)]
            if len(s) == 0:
                print("no attribute in set", att, event_set)
                return True
            res = sum(s) / len(s) >= num
            if not res:
                violation_dict[event_set][1][index] += 1
            return
    # for the span constraint agg_func is the lower, num the upper
    elif mode == SPAN:
        nums = [x for e in event_set for x in case.get_att_for_label(e, att)]
        res = agg_func <= max(nums) - min(nums) <= num
        if not res:
            violation_dict[event_set][1][index] += 1
        return res
    elif mode == GAP:
        # times = [case.events[i].timestamp for i, lab in enumerate(case.trace) if lab in event_set]
        poses = [i for i, lab in enumerate(case.events) if lab.label in event_set]
        if len(poses) < 2:
            return True
        # first = min(poses)
        # last = max(poses)
        # if att == POS:
        #     if last - first > num:
        #         return False
        # elif att == XES_TIME:
        #     first = min(times)
        #     last = max(times)
        #     if (last - first).total_seconds() > num:
        #         return False
        # else:
        #     if case.events[last].attributes[att] - case.events[first].attributes[att] > num:
        #         return False
        # TODO the following evaluates a successive gap, i.e. between every consecutive events
        prev = None
        for i, curr in enumerate(poses):
            if i != 0:
                if att == POS:
                    if curr - prev > num:
                        return False
                elif att == XES_TIME:
                    if (case.events[curr].timestamp - case.events[prev].timestamp).total_seconds() > num:
                        return False
                else:
                    if case.events[curr].attributes[att] - case.events[prev].attributes[att] > num:
                        return False
            prev = curr
        return True
    else:
        return True


def check_existence(log, case, event_set, with_label=False):
    if with_label:
        return all(e in case.unique_event_classes for e in event_set)
    return all(log.unique_event_classes[e] in case.unique_event_classes for e in event_set)


def check_existence_any(log, case, event_set, with_label=False):
    if with_label:
        return any(e in case.unique_event_classes for e in event_set)
    return any(log.unique_event_classes[e] in case.unique_event_classes for e in event_set)


def check_all_constraints_for_case(log, case, event_set, constraints, violation_dict, with_label):
    if with_label:
        return all(check_categorical_with_label(case, violation_dict, index, constraint[0], event_set, constraint[1], constraint[3]) if
                   log.event_att_to_type[constraint[0]] == DataType.CAT else check_numerical_with_label(case, violation_dict, index,
                                                                                                        constraint[0],
                                                                                                        event_set,
                                                                                                        constraint[1],
                                                                                                        constraint[2],
                                                                                                        constraint[
                                                                                                            3]) for
                   index, constraint in enumerate(constraints) if constraint[0] == NUM_GROUPS and constraint[0] != XES_NAME)
    else:
        res = [check_categorical(log, case, violation_dict, index, constraint[0], event_set, constraint[1], constraint[3]) if
                   log.event_att_to_type[constraint[0]] == DataType.CAT else check_numerical(log, case, violation_dict, index,
                                                                                             constraint[0],
                                                                                             event_set,
                                                                                             constraint[1],
                                                                                             constraint[2],
                                                                                             constraint[3]) for
                   index, constraint in enumerate(constraints) if constraint[0] != NUM_GROUPS and constraint[0] != XES_NAME]
        return all(res)


def check_all_constraints_case_based(log, event_set, constraints, handle_loops, handle_xor, handle_concurrent,
                                     with_label=False, on_log=False, frac_to_hold=1.0, violation_dict={}):
    # TODO experimental!!!
    first = True
    if on_log:
        sums = [compute_numerical(log, subcase, SINCE_LAST, event_set, SUM) for case in
                log.cases for subcase in case.subcases if check_existence_any(log, subcase, event_set, with_label)]
        avg = sum(sums) / len(sums)
        first = avg < constraints[0][3]
        return first
    # TODO end experimental
    if handle_loops:
        if handle_xor:
            sums = [check_all_constraints_for_case(log, subcase, event_set, constraints, violation_dict, with_label=with_label) for case
                    in
                    log.cases for subcase in case.subcases if check_existence_any(log, subcase, event_set, with_label)]
            return first and sum(sums) / len(sums) >= frac_to_hold

        else:
            sums = [check_all_constraints_for_case(log, subcase, event_set, constraints,  violation_dict, with_label=with_label) for case
                    in log.cases for subcase in case.subcases if check_existence_any(log, subcase, event_set, with_label)]
            return first and sum(sums) / len(sums) >= frac_to_hold
    else:
        if handle_xor:
            sums = [check_all_constraints_for_case(log, case, event_set, constraints, violation_dict, with_label=with_label) for case
                    in log.cases if check_existence_any(log, case, event_set, with_label)]
            return sum(sums) / len(sums) >= frac_to_hold
        else:
            sums = [check_all_constraints_for_case(log, case, event_set, constraints, violation_dict, with_label=with_label) for case
                in log.cases if check_existence(log, case, event_set, with_label)]
            return sum(sums) / len(sums) >= frac_to_hold


def check_all_constraints_class_based(log, event_set, constraints, violation_dict):
    for index, constraint in enumerate(constraints):
        if constraint[0] == XES_NAME:
            continue
        if constraint[0] == CL:
            if not all([(log.unique_event_classes.index(clc[0]) in event_set and
                         not log.unique_event_classes.index(clc[1]) in event_set) or
                        (log.unique_event_classes.index(clc[1]) in event_set and
                         not log.unique_event_classes.index(clc[0]) in event_set) for clc in constraint[1]]):
                return False
        elif constraint[0] == ML:
            if not all([(log.unique_event_classes.index(clc[0]) in event_set and
                         log.unique_event_classes.index(clc[1]) in event_set) or
                        (not log.unique_event_classes.index(clc[1]) in event_set and
                         not log.unique_event_classes.index(clc[0]) in event_set) for clc in constraint[1]]):
                return False
        else:
            # print(set.union(
            #         *[set(log.get_att_vals_for_ec[log.unique_event_classes[e]][constraint[0]]) for e in event_set]))
            if constraint[1] == EXACTLY and not len(set.union(
                    *[set(log.get_att_vals_for_ec[log.unique_event_classes[e]][constraint[0]]) for e in event_set])) == constraint[3]:
                violation_dict[event_set][0][index] = 1
                return False
            elif constraint[1] == MAX and not len(set.union(
                    *[set(log.get_att_vals_for_ec[log.unique_event_classes[e]][constraint[0]]) for e in event_set])) <= constraint[3]:
                violation_dict[event_set][0][index] = 1
                return False
            elif constraint[1] == MIN and not len(set.union(
                    *[set(log.get_att_vals_for_ec[log.unique_event_classes[e]][constraint[0]]) for e in event_set])) >= constraint[3]:
                violation_dict[event_set][0][index] = 1
                return False
    return True


########################################################################################################################
########################################################################################################################

def compute_numerical(log, case, att, event_set, agg_func):
    if agg_func == SUM:
        return sum([x for e in event_set for x in case.get_att_for_label(log.unique_event_classes[e], att)])
    elif agg_func == AVG:
        s = [x for e in event_set for x in case.get_att_for_label(log.unique_event_classes[e], att)]
        if len(s) == 0:
            print("no attribute in set", att, event_set)
            return True
        return sum(s) / len(s)
