import random
import string
from collections import deque
from datetime import datetime, timedelta
from const import *

import numpy as np

from eval.discovery import dfg

DISTS = ["normal", "exponential"]
DURATION_RANGE = (1, 10000)


def sample_from_normal(mu=5, sigma=1, num_samples=10000):
    s = np.random.normal(mu, sigma, num_samples)
    return s


def sample_from_exponential(scale, num_samples=10000):
    s = np.random.exponential(scale, num_samples)
    return s


def sample_time_att(pm4py_log):
    unique_event_classes = list(set([event[XES_NAME] for case in pm4py_log for event in case]))
    sample_dict = {}
    param_dict = {}
    for cls in unique_event_classes:
        dist_type = random.choice(DISTS)
        me = random.choice(range(*DURATION_RANGE))
        param_dict[cls] = (dist_type, me, me/10)
        sample_dict[cls] = deque(sample_from_normal(mu=param_dict[cls][1], sigma=param_dict[cls][2])) if param_dict[cls][0] == "normal" else deque(sample_from_exponential(scale=param_dict[cls][1]))
    for trace in pm4py_log:
        zero_time = datetime(2021, 5, 1)
        current_time = zero_time
        current_event = trace[0]
        trace[0][XES_TIME] = current_time
        for i in range(1, len(trace)):
            rand = sample_dict[current_event[XES_NAME]].pop()
            while rand < 0:
                rand = sample_dict[trace[i][XES_NAME]].pop()
            time_change = timedelta(minutes=rand)
            current_time = current_time + time_change
            trace[i][XES_TIME] = current_time
            current_event = trace[i]


def sample_cat_att(pm4py_log, name, length=4):
    # printing lowercase
    letters = string.ascii_lowercase
    unique_event_classes = list(set([event[XES_NAME] for case in pm4py_log for event in case]))
    num = random.choice(list(range(2, len(unique_event_classes) + 1)))
    values = []
    for _ in range(num):
        values.append(''.join(random.choice(letters) for _ in range(length)))
    class_to_att = dict()
    for clz in unique_event_classes:
        class_to_att[clz] = random.choice(values)
    for trace in pm4py_log:
        for event in trace:
            event[name] = class_to_att[event[XES_NAME]]


"""
mean_num = len(unique_event_classes)/4
    stddev = mean_num/4
    num = random.choice(list(range(2, len(unique_event_classes)+1)))
    values = []
    for _ in range(num):
        values.append(''.join(random.choice(letters) for _ in range(length)))
    dist_type = random.choice(DISTS)
    if dist_type == "normal":
        distrib = sample_from_normal(mu=0.5, sigma=0.5)
    else:
        distrib = sample_from_exponential(scale=1.0, num_samples=len(values))
    distrib = [x/sum(distrib) for x in distrib]
"""