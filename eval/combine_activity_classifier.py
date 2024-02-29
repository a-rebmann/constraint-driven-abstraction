import sys

from const import REAL_LOGS_DIR, XES_NAME, XES_LIFECYCLE
from readwrite import read_basic_pm4py, write_xes

if __name__ == "__main__":
    pm4py = read_basic_pm4py("../" + REAL_LOGS_DIR, "bpi13i.xes")
    for case in pm4py:
        for event in case:
            event[XES_NAME] = str(event[XES_NAME]+"-"+event[XES_LIFECYCLE])

    write_xes("../" + REAL_LOGS_DIR, "bpic13i"+"l", pm4py)
    sys.exit(0)