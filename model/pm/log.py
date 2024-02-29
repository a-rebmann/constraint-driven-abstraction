from datetime import datetime
#from extraction import extract
from model.datatype import DataType
from model.pm.case import Case
from model.pm.event import Event
from model.pm.dfg_util import to_real_graph_encoded
from numbers import Number
from const import XES_BASIC, XES_NAME, XES_TIME, OBJECT, ACTION, SINCE_START, SINCE_LAST, POS, WEEKDAY, DAY, \
    TERMS_FOR_MISSING
import random
import numpy as np
import pandas as pd
from eval.discovery import dfg
from pm4py.algo.filtering.log.variants import variants_filter
from pm4py.statistics.attributes.log import get as attr_get
from pm4py.statistics.start_activities.log import get as start_get
from pm4py.statistics.end_activities.log import get as end_get


class Log(object):

    def __init__(self, cases, name='default', target=None, pm4py=None, split_loops={}):
        self.pm4py = pm4py
        self.cases = cases
        self.num_cases = len(cases)
        self.name = name
        self.target = target
        self.case_id = 'case:' + XES_NAME
        self.event_label = XES_NAME
        self.activity_value_counts = attr_get.get_attribute_values(self.pm4py, self.event_label,
                                                                   parameters={}) if self.pm4py is not None else None
        self.group_by_case = None
        self.resource = None
        self.timestamp = XES_TIME
        self._case_att_to_type = None
        self._constant_event_attributes = None
        self._dynamic_event_attributes = None
        self._event_att_to_type = None
        self._traces = None
        self._target_traces = None
        self._variants = variants_filter.get_variants(self.pm4py) if self.pm4py is not None else None
        self._start_activities = start_get.get_start_activities(self.pm4py) if self.pm4py is not None else None
        self._end_activities = None
        self.split_loops = split_loops
        self.event_vectors = None
        self.targets = None
        self.encoders = None
        self.scalers = None
        self._unique_classes = list(set([event.label for case in self.cases for event in case.events]))
        self._encoded_classes = list(range(len(self._unique_classes)))
        self.event_set_co_occurs = dict()
        self.dfg_dict = dfg(self.pm4py, viz=False)
        self._dfg_encoded = None
        self._weak_order_matrix = None
        self._behavioral_profile = None
        self.xor_sets = dict()
        self.pre_succ_to_groups = dict()
        self.ec_to_att_vals = None

    @property
    def event_att_to_type(self):
        if self._event_att_to_type is None:
            atts = {XES_NAME: DataType.CAT, XES_TIME: DataType.TIME, WEEKDAY: DataType.CAT, DAY: DataType.CAT}
            for c in self.cases:
                for e in c.events:
                    for key in e.attributes.keys():
                        if key not in atts and key not in XES_BASIC:
                            if isinstance(e.attributes[key], datetime):
                                atts[key] = DataType.TIME
                            else:
                                atts[key] = DataType.NUM if isinstance(e.attributes[key], Number) else DataType.CAT
            self._event_att_to_type = atts
        return self._event_att_to_type

    @property
    def case_att_to_type(self):
        if self._case_att_to_type is None:
            atts = {XES_NAME: DataType.CAT}
            for c in self.cases:
                for key in c.attributes.keys():
                    if key not in atts and key not in XES_BASIC:
                        if isinstance(c.attributes[key], datetime):
                            atts[key] = DataType.TIME
                        else:
                            atts[key] = DataType.NUM if isinstance(c.attributes[key], Number) else DataType.CAT
            self._case_att_to_type = atts
        return self._case_att_to_type

    @property
    def constant_event_attributes(self):
        if self._constant_event_attributes is None:
            self._constant_event_attributes = list()
            for att in self.event_att_to_type.keys():
                if len(self.get_unique_event_att_vals(att)) <= 2:
                    self._constant_event_attributes.append(att)
        return self._constant_event_attributes

    @property
    def dynamic_event_attributes(self):
        if self._dynamic_event_attributes is None:
            self._dynamic_event_attributes = list()
            for att in self.event_att_to_type.keys():
                if len(self.get_unique_event_att_vals(att)) > 2:
                    self._dynamic_event_attributes.append(att)
        return self._dynamic_event_attributes

    @property
    def dfg_encoded(self):
        if self._dfg_encoded is None:
            self._dfg_encoded = to_real_graph_encoded(self)
        return self._dfg_encoded

    def get_unique_event_att_vals(self, key):
        return list(set([str(e.attributes[key]) if key in e.attributes else '' for c in self.cases for e in c.events]))

    def get_unique_case_att_vals(self, key):
        return sorted(list(set([str(c.attributes[key]) if key in c.attributes else '' for c in self.cases])))

    @property
    def get_att_vals_for_ec(self):
        if self.ec_to_att_vals is None:
            self.ec_to_att_vals = dict()
            for ec in self.unique_event_classes:
                self.ec_to_att_vals[ec] = dict()
                for key in self.event_att_to_type.keys():
                    if self.event_att_to_type[key] == DataType.CAT:
                        res = list(set([e.attributes[key] if key in e.attributes and e.attributes[key] not in TERMS_FOR_MISSING else '' for c in self.cases for e in c.events if e.label == ec]))
                        self.ec_to_att_vals[ec][key] = [r for r in res if r != '']
        return self.ec_to_att_vals

    @property
    def unique_event_classes(self):
        return self._unique_classes

    @property
    def encoded_event_classes(self):
        if self._encoded_classes is None:
            self._encoded_classes = list(range(len(self._unique_event_classes)))
        return self._encoded_classes

    @property
    def variants(self):
        return self._variants

    @property
    def activity_counts(self):
        if self.activity_value_counts is None:
            d = attr_get.get_attribute_values(self.pm4py, self.evet_label, parameters={})
            self.activity_value_counts = d
        return self.activity_value_counts

    @property
    def start_activities(self):
        if self._start_activities is None:
            self._start_activities = start_get.get_start_activities(self.pm4py)
        return self._start_activities

    @property
    def end_activities(self):
        if self._end_activities is None:
            self._end_activities = end_get.get_end_activities(self.pm4py)
        return self._end_activities

    def get_unique_target_event_classes(self):
        if self.target is None:
            return None
        return list(set([t_event for trace in self.target_traces for t_event in trace]))

    @property
    def traces(self):
        if self._traces is None:
            self._traces = [c.trace for c in self.cases]
        return self._traces

    @property
    def target_traces(self):
        if self._target_traces is None:
            self._target_traces = [c.target_trace for c in self.cases]
        return self._target_traces

    def add_roles(self, add_bo, add_action):
        """
        Adds semantic roles to the event log, which are contained in the event name
        Parameters
        ----------
        add_bo
        add_action

        Returns
        -------

        """
        # extractor = extract.get_instance()
        # label_to_role = extractor.extract_roles_from_list_of_labels(self.unique_event_classes)
        # for c in self.cases:
        #     for e in c.events:
        #         if add_bo:
        #             if OBJECT in label_to_role[e.label].keys():
        #                 bos = label_to_role[e.label][OBJECT]
        #                 e.attributes[OBJECT] = bos[0]
        #             else:
        #                 e.attributes[OBJECT] = ""
        #         if add_action:
        #             if ACTION in label_to_role[e.label].keys():
        #                 actions = label_to_role[e.label][ACTION]
        #                 e.attributes[ACTION] = actions[0]
        #             else:
        #                 e.attributes[ACTION] = ""

    def add_target(self, target):
        self.target = target
        for c in self.cases:
            target_events = []
            if self.target is not None:
                target_events = [Event(e.attributes[self.target], e.timestamp, **{}) for e in c.events]
                for e in c.events:
                    del e.attributes[self.target]
            c.target_events = target_events

    def subcases(self, case):
        if case.variant_str in self.split_loops.keys():
            return [case.events[i[0]:i[1]] for i in self.split_loops[case.variant_str]]
        else:
            return [case.events]

    def split(self, ratio=.5, rand=True):
        cases1 = []
        cases2 = []
        pct_index = int(ratio * len(self.cases))
        if rand:
            idx = list(range(0, len(self.cases)))
            random.shuffle(idx)
            idx = idx[:pct_index]
            for i, _ in enumerate(self.cases):
                if i in idx:
                    cases1.append(self.cases[i])
                else:
                    cases2.append(self.cases[i])
        else:
            cases1 = self.cases[:pct_index]
            cases2 = self.cases[pct_index:]
        return Log(cases1, self.name + '_split1', self.target), Log(cases2, self.name + '_split2', self.target)

    def _get_weak_order_matrix(self, as_df=False):
        wom = np.zeros(shape=(len(self.unique_event_classes), len(self.unique_event_classes)))
        for case in self.cases:
            for scase in case.subcases:
                activities = scase.trace
                for i in range(0, len(activities) - 1):
                    for j in range(i + 1, len(activities)):
                        wom[self.unique_event_classes.index(activities[i]), self.unique_event_classes.index(
                            activities[j])] += 1
        if as_df:
            return pd.DataFrame(wom, columns=self.unique_event_classes, index=self.unique_event_classes)
        return wom

    def get_behavioral_profile_as_df(self):
        wom = self._get_weak_order_matrix(as_df=True)
        cols = wom.columns
        wom = wom.values
        wom_len = len(wom)
        res = np.empty((wom_len, wom_len), dtype=float)
        strict_order, reverse_strict_order, exclusive, interleaving = set(), set(), set(), set()
        for i in range(wom_len):
            for j in range(wom_len):
                if i == j:  res[i, j] = 4; continue
                if wom[i, j] == 0 and wom[j, i] != 0: res[j, i] = 0; strict_order.add((cols[i], cols[j])); continue
                if wom[j, i] == 0 and wom[i, j] != 0: res[j, i] = 1; reverse_strict_order.add(
                    (cols[i], cols[j])); continue
                if wom[i, j] != 0 and wom[j, i] != 0: res[j, i] = 2; interleaving.add((cols[i], cols[j])); continue
                if wom[i, j] == 0 and wom[j, i] == 0: res[j, i] = 3; exclusive.add((cols[i], cols[j])); continue
        return pd.DataFrame(res, columns=cols, index=cols).replace([0, 1, 2, 3, 4], ['-->', "<--", "||", "+", ""])

    @property
    def behavioral_profile(self):
        if self._behavioral_profile is None:
            wom = self._get_weak_order_matrix(as_df=True)
            cols = wom.columns
            wom = wom.values
            wom_len = len(wom)
            res = np.empty((wom_len, wom_len), dtype=float)
            strict_order, reverse_strict_order, exclusive, interleaving = set(), set(), set(), set()
            for i in range(wom_len):
                for j in range(wom_len):
                    if i == j:  res[i, j] = 4; continue
                    if wom[i, j] == 0 and wom[j, i] != 0: res[j, i] = 0; strict_order.add((cols[i], cols[j])); continue
                    if wom[j, i] == 0 and wom[i, j] != 0: res[j, i] = 1; reverse_strict_order.add(
                        (cols[i], cols[j])); continue
                    if wom[i, j] != 0 and wom[j, i] != 0: res[j, i] = 2; interleaving.add((cols[i], cols[j])); continue
                    if wom[i, j] == 0 and wom[j, i] == 0: res[j, i] = 3; exclusive.add((cols[i], cols[j])); continue
            self._behavioral_profile = {'strict_order': strict_order, 'reverse_strict_order': reverse_strict_order, 'exclusive':exclusive, 'interleaving':interleaving}
        return self._behavioral_profile

    def get_med_num_unique_per_case(self, att):
        import statistics
        num_att_per_case = [len(set([event[att] for case in self.pm4py for event in case]))]
        return statistics.median(num_att_per_case)

    def get_mean_case_dur(self):
        import statistics
        num_att_per_case = [int(case.events[-1].timestamp - case.events[0].timestamp) for case in self.pm4py]
        return statistics.mean(num_att_per_case)


def from_pm4py_event_log(log, name, target=None):
    """
    :param log: a pm4py log
    :param name: the name of this log
    :param target: the target attribute, i.e. the optimization attribute if available
    :return: a custom log representation
    """
    cases = []

    # here we want to split the traces whenever we encounter a recurrent activity.
    # We save the sub-traces as a list of tuples of the positions of the first and last event of a sub-trace
    split_loops = {}
    variants = variants_filter.get_variants(log)
    for variant in variants.keys():
        var_list = variant.split(',')
        split_loops[variant] = split_into_subtraces(var_list)
    for c in log:
        events = [Event(e[XES_NAME], e[XES_TIME], **e) for e in c]
        case_start = events[0].timestamp
        events[0].attributes[SINCE_START] = 0
        events[0].attributes[SINCE_LAST] = 0
        events[0].attributes[POS] = 0
        for i in range(1, len(events)):
            events[i].attributes[SINCE_LAST] = (events[i].timestamp - events[i - 1].timestamp).total_seconds()
            events[i].attributes[SINCE_START] = (events[i].timestamp - case_start).total_seconds()
            events[i].attributes[POS] = i
        target_events = None
        if target is not None:
            target_events = [Event(e[target], e[XES_TIME], **{}) for e in c]
        case = Case(c.attributes[XES_NAME], events, target_events, **c.attributes)
        case._non_redundant_parts = split_loops[case.variant_str]
        if target is not None:
            for e in case.events:
                del e.attributes[target]
        cases.append(case)
    return Log(cases, name, target, pm4py=log, split_loops=split_loops)


def split_into_subtraces(variant):
    variants_pos = []
    variants = []
    current = []
    current_pos = []
    for i, event in enumerate(variant):
        if event not in current:
            current.append(event)
            current_pos.append(i)
        else:
            variants_pos.append(current_pos)
            current = [event]
            current_pos = [i]
    variants_pos.append(current_pos)
    for variant in variants_pos:
        variants.append((variant[0], variant[-1]))
    return variants
