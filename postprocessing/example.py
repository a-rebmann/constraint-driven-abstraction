from copy import deepcopy
from pm4py.objects.log.importer.xes import importer as xes_importer

log = xes_importer.apply('<path_to_xes_file.xes>')

mapping = {"event_label_1": "activity_label_A", "event_label_2": "activity_label_A",
           "event_label_3": "activity_label_A", "event_label_4": "activity_label_B",
           "event_label_5": "activity_label_B"}
only_complete = False


for trace in log:
    new_trace = list()
    for event in trace:
        event["concept:name"] = mapping[event["concept:name"]]
        print(event["concept:name"] + " is not a low-level event. Caught key error.")
    trace.sort(key=lambda x: x["time:timestamp"], reverse=False)
    if not only_complete:
        firsts = dict()
        for event in trace:
            if event["concept:name"] not in firsts.keys():
                new_event = deepcopy(event)
                new_event["lifecycle:transition"] = "start"
                firsts[event["concept:name"]] = new_event
        new_trace.extend(firsts.values())
    lasts = dict()
    reverse_iterator = reversed(trace)
    for event in reverse_iterator:
        if event["concept:name"] not in lasts.keys():
            new_event = deepcopy(event)
            new_event["lifecycle:transition"] = "complete"
            lasts[event["concept:name"]] = new_event
    new_trace.extend(lasts.values())
    new_trace.sort(key=lambda x: x["time:timestamp"], reverse=False)
    trace._list = new_trace


# Das hier splitted einen Trace sobald sich ein event label wiederholt (Schleife). Damit kann man mehrere Instanzen von
# Activities erzeugen

def split_into_subtraces(trace_to_split):
    variants = []
    current = []
    current_names = []
    for e in trace_to_split:
        if e["concept:name"] not in current_names:
            current.append(e)
            current_names.append(e["concept:name"])
        else:
            variants.append(current)
            current = [e]
            current_names = [e["concept:name"]]
    variants.append(current)
    return variants


for t in log:
    new_trace = list()
    for trace in split_into_subtraces(t):
        for event in trace:
            try:
                event["concept:name"] = mapping[event["concept:name"]]
            except KeyError:
                print(event["concept:name"] + " is not a low-level event. Caught key error.")
        trace.sort(key=lambda x: x["time:timestamp"], reverse=False)
        if not only_complete:
            firsts = dict()
            for event in trace:
                if event["concept:name"] not in firsts.keys():
                    new_event = deepcopy(event)
                    new_event["lifecycle:transition"] = "start"
                    firsts[event["concept:name"]] = new_event
            new_trace.extend(firsts.values())
        lasts = dict()
        reverse_iterator = reversed(trace)
        for event in reverse_iterator:
            if event["concept:name"] not in lasts.keys():
                new_event = deepcopy(event)
                new_event["lifecycle:transition"] = "complete"
                lasts[event["concept:name"]] = new_event
        new_trace.extend(lasts.values())
    new_trace.sort(key=lambda x: x["time:timestamp"], reverse=False)
    t._list = new_trace