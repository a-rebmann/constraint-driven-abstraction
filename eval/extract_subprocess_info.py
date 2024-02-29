import sys

from const import REAL_LOGS_DIR, XES_NAME
from readwrite import read_basic_pm4py, write_xes

bpic15 = ["bpi151f.xes"]

if __name__ == "__main__":
    for bpic in bpic15:
        pm4py = read_basic_pm4py("../" + REAL_LOGS_DIR, bpic)
        for case in pm4py:
            for event in case:
                if event[XES_NAME] == "START" or event[XES_NAME] == "END":
                    event["SP1"] = event[XES_NAME]
                    event["SP2"] = event[XES_NAME]
                    continue
                event["SP1"] = str(event[XES_NAME].split('_')[0] + "_" + event[XES_NAME].split('_')[1])
                event["SP2"] = str(event[XES_NAME].split('_')[0] + "_" + event[XES_NAME].split('_')[1] + "_" +
                                   event[XES_NAME].split('_')[2][0])

        write_xes("../" + REAL_LOGS_DIR, bpic.replace(".xes", "") + "sp", pm4py)
    sys.exit(0)
