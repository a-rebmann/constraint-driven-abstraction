from const import STANDARD_TARGET_KEY


def add_hierarchical_attributes(log_file, event_log):
    if "12" in log_file:
        for case in event_log.cases:
            for event in case.events:
                event.attributes[STANDARD_TARGET_KEY] = str(event.label.split('_')[0])
        event_log.add_target(STANDARD_TARGET_KEY)
    elif "15" in log_file:
        for case in event_log.cases:
            for event in case.events:
                if event.label == 'START' or event.label == 'END':
                    event.attributes[STANDARD_TARGET_KEY] = str(
                        event.label)
                else:
                    event.attributes[STANDARD_TARGET_KEY] = str(
                        event.label.split('_')[0] + event.label.split('_')[1])
        event_log.add_target(STANDARD_TARGET_KEY)
    else:
        print("We only have hierarchical info encoded in the label for BPI 12 and 17")


def synthetic_log_settings():
    seq_probs = [0.3, 0.4, 0.5, 0.6, 0.7]
    xor_probs = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    and_probs = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    loop_probs = [0.0, 0.1, 0.2, 0.3]
    configs = list()
    for seq_prob in seq_probs:
        for xor_prob in xor_probs:
            for and_prob in and_probs:
                for loop_prob in loop_probs:
                    if seq_prob + xor_prob + and_prob + loop_prob == 1.0 and (seq_prob, xor_prob, and_prob, loop_prob) not in configs:
                        configs.append((seq_prob, xor_prob, and_prob, loop_prob))
    for config in configs:
        print(config)
    print(len(configs))


