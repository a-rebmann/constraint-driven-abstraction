def group_wise_interleaving_variants(event_set, log, handle_loops, handle_xor, handle_concurrent):
    """
    Returns the group-wise interleaving measure as well as the count of co-occurrence for the given group
    Parameters
    ----------
    handle_loops
    handle_xor
    handle_concurrent
    event_set
    log

    Returns a tuple dist, occ
    -------

    """
    sum_up = 0
    num = 0
    actually_cooccurs = False
    for variant in log.variants.keys():
        var_list = variant.split(',')
        var_list = [log.unique_event_classes.index(v) for v in var_list]
        if handle_loops and variant in log.split_loops.keys():
            var_lists = [var_list[i[0]:(i[1]+1)] for i in log.split_loops[variant]]
        else:
            var_lists = [var_list]
        num_cases = len(log.variants[variant])
        interleavings_per_subcase = []
        for sub_variant in var_lists:
            if all(i in sub_variant for i in event_set):
                actually_cooccurs = True
            if any(i in sub_variant for i in event_set):
                poses = [i for i, lab in enumerate(sub_variant) if lab in event_set]
                first = min(poses)
                last = max(poses)
                span = 1 + (last - first)
                interleaving = (span - len(poses)) / len(poses)
                missing = (len(event_set) - len(poses)) / len(event_set)
                curr = interleaving + missing + (1 / len(event_set))
                interleavings_per_subcase.append(curr)
        if len(interleavings_per_subcase) > 0:
            sum_up += sum(interleavings_per_subcase)
            num += len(interleavings_per_subcase) * num_cases
    return (sum_up/num, actually_cooccurs) if num > 0 else (float("inf"), actually_cooccurs)


def get_groupwise_interleaving_xor(event_set, log, handle_loops, handle_concurrent):
    # In this case a variant contains not all types of events, however,
    # we might encounter a strict exclusion within a group
    sum_up = 0
    num = 0
    for variant in log.variants.keys():
        var_list = variant.split(',')
        var_list = [log.unique_event_classes.index(v) for v in var_list]
        if handle_loops and variant in log.split_loops.keys():
            var_lists = [var_list[i[0]:(i[1] + 1)] for i in log.split_loops[variant]]
        else:
            var_lists = [var_list]
        num_cases = len(log.variants[variant])
        interleavings_per_subcase = []
        for sub_variant in var_lists:
            if any(i in sub_variant for i in event_set):
                poses = [i for i, lab in enumerate(sub_variant) if lab in event_set]
                first = min(poses)
                last = max(poses)
                span = 1 + (last - first)
                interleaving = (span - len(poses)) / len(poses)
                missing = (len(event_set) - len(poses)) / len(event_set)
                curr = interleaving + missing + 1 / len(event_set)
                interleavings_per_subcase.append(curr)
        if len(interleavings_per_subcase) > 0:
            sum_up += sum(interleavings_per_subcase)
            num += len(interleavings_per_subcase) * num_cases
    return sum_up / num if num > 0 else float("inf")



