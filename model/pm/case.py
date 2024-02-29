from const import TERMS_FOR_MISSING, XES_TIME, XES_NAME


class Case(object):

    def __init__(self, case_id, events, targets, **kwargs):
        self.id = case_id
        self.events = events
        self.target_events = targets
        self._trace = None
        self._non_redundant_parts = []
        self._subcases = None
        self.attributes = dict(kwargs)
        self._unique_classes = None
        self.clz_to_att = {}

    @property
    def trace(self):
        if self._trace is None:
            self._trace = [str(event.label) for event in self.events]
        return self._trace

    @property
    def variant_str(self):
        return ",".join(self.trace)

    @property
    def unique_event_classes(self):
        if self._unique_classes is None:
            self._unique_classes = list(set([event.label for event in self.events]))
        return self._unique_classes

    def get_att_for_label(self, label, att):
        if (label, att) not in self.clz_to_att.keys():
            if att == XES_NAME:
                self.clz_to_att[(label, att)] = [label]
            elif att == XES_TIME:
                self.clz_to_att[(label, att)] = [event.timestamp for event in self.events if
                                                 event.label == label and event.timestamp not in TERMS_FOR_MISSING]
            else:
                self.clz_to_att[(label, att)] = [event.attributes[att] for event in self.events if att in event.attributes and
                                                 event.label == label and event.attributes[att] not in TERMS_FOR_MISSING]
        return self.clz_to_att[(label, att)]

    @property
    def subcases(self):
        if self._subcases is None:
            self._subcases = []
            for i, part in enumerate(self._non_redundant_parts):
                self._subcases.append(Case(case_id=self.id+'_'+str(i), events=self.events[part[0]:part[1]+1], targets=None))
        return self._subcases

    @property
    def target_trace(self):
        if self._trace is None:
            self._trace = [str(event.label) for event in self.target_events]
        return self._trace

    def att_trace(self, att):
        return [e.attributes[att] for e in self.events]

    def target_att_trace(self, att):
        if self.target_events is None:
            return None
        return [e.attributes[att] for e in self.target_events]
