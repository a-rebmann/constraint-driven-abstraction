from functools import total_ordering


class Group:

    def __init__(self, members: frozenset, skip_checking=False):
        self.members = members
        self.skip_checking = skip_checking

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.members == other.members

    def __hash__(self):
        return hash(self.members)


class XORGroup(Group):

    def __init__(self, members, succ: set, pred: set):
        super().__init__(members)
        self.succ = succ
        self.pred = pred


    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.members == other.members

    def __hash__(self):
        return hash(self.members)

    def __repr__(self):
        return str(self.members)


@total_ordering
class PrioritizedGroup(Group):
    def __init__(self, priority, members, path, fulfils_requirements=False):
        super().__init__(members)
        self.priority = priority
        self.path = path
        self.fulfils_requirements = fulfils_requirements

    def __eq__(self, other):
        if not isinstance(other, __class__):
            return NotImplemented
        return self.priority == other.priority

    def __hash__(self):
        return hash(self.members)

    def __lt__(self, other):
        if not isinstance(other, __class__):
            return NotImplemented
        return self.priority < other.priority


@total_ordering
class SimplePrioritizedGroup(Group):
    def __init__(self, priority, members):
        super().__init__(members)
        self.priority = priority

    def __eq__(self, other):
        if not isinstance(other, __class__):
            return NotImplemented
        return self.priority == other.priority

    def __hash__(self):
        return hash(self.members)

    def __lt__(self, other):
        if not isinstance(other, __class__):
            return NotImplemented
        return self.priority < other.priority
