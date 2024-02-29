from const import CLASS_BASED, INSTANCE_BASED, MAX, MIN


def get_num_cases(log):
    return sum([1 for case in log.cases for subcase in case.subcases])


def provide_feedback_about_constraints(violation_dict, constraint_dict, log, frac=0.2):
    print("-" * 40)
    print("FEEDBACK")
    print("-" * 40)
    print("The following information may be useful to adapt your constraints:\n")
    constraint_violations = {constraint: {ec: 0 for ec in log.encoded_event_classes} for val in constraint_dict.values() for constraint in val}
    constraint_violations_total = {constraint: 0 for val in constraint_dict.values() for constraint in val}

    min_key, min_value = min(violation_dict.items(), key=lambda x: len(set(x[0])))
    max_key, max_value = max(violation_dict.items(), key=lambda x: len(set(x[0])))
    for event_set, violations in violation_dict.items():
        for index, constraint in enumerate(constraint_dict[CLASS_BASED]):
            if violations[0][index] > 0:
                constraint_violations_total[constraint] += 1
                for ec in event_set:
                    constraint_violations[constraint][ec] += 1

        for index, constraint in enumerate(constraint_dict[INSTANCE_BASED]):
            if violations[1][index]/get_num_cases(log) >= frac:
                if constraint[1] == MAX and len(event_set) == len(min_key):
                    print("The group", [log.unique_event_classes[i] for i in event_set],
                          "violated the instance-based constraint", str(constraint).replace(", None", ""), "in",
                          "{:.2f}".format(violations[1][index] / get_num_cases(log) * 100), "percent of the cases.")
                elif constraint[1] == MIN and ((len(event_set) == len(max_key)) or (len(event_set) == len(max_key)-1)):
                    print("The group", [log.unique_event_classes[i] for i in event_set],
                          "violated the instance-based constraint", str(constraint).replace(", None", ""), "in",
                          "{:.2f}".format(violations[1][index] / get_num_cases(log) * 100), "percent of the cases.")
                elif constraint[1] != MIN and len(event_set) == len(min_key):
                    print("The group", [log.unique_event_classes[i] for i in event_set],
                          "violated the instance-based constraint", str(constraint).replace(", None", ""), "in",
                          "{:.2f}".format(violations[1][index]/get_num_cases(log)*100), "percent of the cases.")
            if violations[1][index] > 0:
                constraint_violations_total[constraint] += 1
                for ec in event_set:
                    constraint_violations[constraint][ec] += violations[1][index]

    for constraint in constraint_violations:
        if constraint in constraint_dict[INSTANCE_BASED]:
            if constraint_violations_total[constraint] / len(violation_dict.keys()) > 0.5:
                print("The instance-based constraint", str(constraint).replace(", None", ""), "was violated by", "{:.2f}".format((constraint_violations_total[constraint] / len(violation_dict.keys()))*100), "percent of the groups at least once")
        if constraint in constraint_dict[CLASS_BASED]:
            if constraint_violations_total[constraint] / len(violation_dict.keys()) > 0.5:
                print("The class-based constraint", str(constraint).replace(", None", ""), "was violated by",
                      "{:.2f}".format((constraint_violations_total[constraint] / len(violation_dict.keys())) * 100),
                      "percent of the candidate groups")
            if not constraint_violations_total[constraint] / len(violation_dict.keys()) == 1:
                print("When a group violated the class-based constraint", str(constraint).replace(", None", ""), "the following event classes "
                                                                                      "were frequently contained")
                min_violations = min(constraint_violations[constraint].values())
                # max_violations = max(constraint_violations[constraint].values())
                for ec, freq in constraint_violations[constraint].items():
                    if freq > 2 * min_violations:
                        print(log.unique_event_classes[ec], freq, "times")
    print("-" * 40)
    # print(constraint_violations_total)
    # print(constraint_violations)
    #print(violation_dict)
    # print(len(violation_dict.keys()))