import os
import sys
from const import XES_LIFECYCLE, XES_RESOURCE

from pm4py.objects.log.importer.xes import importer as xes_importer

from pm4py.objects.log.exporter.xes import exporter as xes_exporter

from eval.sampling import sample_time_att, sample_cat_att

SYNTHETIC_LOGS = "../resources/raw/synthetic/"


def augment_log(log):
    sample_time_att(log)
    sample_cat_att(log, XES_RESOURCE, 10)
    for trace in log:
        for event in trace:
            event[XES_LIFECYCLE] = "complete"


def augment_logs():
    for (dir_path, dir_names, filenames) in os.walk(SYNTHETIC_LOGS):
        for filename in filenames:
            if ".xes" not in filename:
                continue
            print("Augmenting log " + filename)
            log = xes_importer.apply(os.path.join(dir_path, filename))
            augment_log(log)
            xes_exporter.apply(log, os.path.join(dir_path, filename))
    sys.exit(0)


if __name__ == "__main__":
    augment_logs()
