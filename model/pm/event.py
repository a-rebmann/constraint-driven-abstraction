from const import WEEKDAY, DAY


class Event(object):

    def __init__(self, label, timestamp=None, **kwargs):
        self.label = label
        self.timestamp = timestamp
        self.attributes = dict(kwargs)
        if self.timestamp is not None:
            self.attributes[WEEKDAY] = self.timestamp.weekday()
            self.attributes[DAY] = str(self.timestamp.year) + str(self.timestamp.month) + str(self.timestamp.day)



    def __repr__(self):
        return f'Event(label={self.label}, time={self.timestamp}, attributes={self.attributes})'