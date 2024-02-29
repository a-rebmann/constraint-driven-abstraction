import matplotlib.pyplot as plt
from supervenn import supervenn

import numpy as np


def visualize_set_overlap(sets):
    supervenn(sets, side_plots=False)
    plt.show()


def dotted_chart(log, num_cases=100):
    X = dict()
    Y = dict()
    ids = []
    for case in log.cases:
        if len(ids) == num_cases:
            break
        ids.append(case.id)
        for i, e in enumerate(case.events):
            (a, x) = case.events[i].label, case.events[i].timestamp
            if a not in X:
                X[a] = []
                Y[a] = []

            X[a].append(x)
            Y[a].append(case.id)
    for a in sorted(X.keys()):
        plt.plot(X[a], Y[a], 'o', label=a,
                                        markersize=20, markeredgewidth=0., alpha=0.5)
    axes = plt.gca()
    axes.set_yticks(range(len(ids)))
    axes.set_ylim(-1, len(ids))
    axes.set_yticklabels(ids)
    axes.set_ylabel('case id')
    axes.invert_yaxis()
    axes.set_xlabel('timestamp')
    axes.xaxis.tick_top()
    axes.xaxis.set_label_position('top')
    plt.grid(True)
    plt.legend(numpoints=1)
    plt.tight_layout()
    plt.show()


def plot_dist_matrix(event_log, matrix):
    fig, ax = plt.subplots()
    plt.figure(dpi=360)
    ax.imshow(matrix)
    # We want to show all ticks...
    ax.set_xticks(np.arange(len(event_log.unique_event_classes)))
    ax.set_yticks(np.arange(len(event_log.unique_event_classes)))
    # ... and label them with the respective list entries
    ax.set_xticklabels(event_log.unique_event_classes, fontsize=5)
    ax.set_yticklabels(event_log.unique_event_classes, fontsize=5)
    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
             rotation_mode="anchor")

    # Loop over data dimensions and create text annotations.
    # for i in range(len(event_log.get_unique_event_classes)):
    #    for j in range(len(event_log.get_unique_event_classes)):
    #        ax.text(j, i, sims[i, j],
    #                       ha="center", va="center", color="w")

    ax.set_title("Distance Matrix.")
    plt.show()