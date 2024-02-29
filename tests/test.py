import sys
import unittest

from eval.config import Config
from evaluation_synthetic import get_synthetic_logs
from main import read, from_pm4py_event_log, abstract_log
from const import *
from readwrite import read_basic_pm4py

SYNTHETIC_CAT_AM_GUARANTEE = [(XES_RESOURCE, MAX, None, 2)]
SYNTHETIC_CAT_M_GUARANTEE = [(XES_RESOURCE, MIN, None, 2)]
SYNTHETIC_NUM_AM_GUARANTEE = [(SINCE_LAST, MAX, SUM, 2 * 60 * 60)]
SYNTHETIC_NUM_M_GUARANTEE = [(SINCE_LAST, MIN, SUM, 200 * 60 * 60)]
SYNTHETIC_NUM_NM_GUARANTEE = [(SINCE_LAST, MAX, AVG, 2 * 60 * 60)]
SYNTHETIC_K_GROUPS_GUARANTEE = [(NUM_GROUPS, MIN, None, 3)]

_configs_basic = [
    Config(efficient=False, guarantees=SYNTHETIC_CAT_AM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           store_groups=False, xes=False),
    Config(efficient=False, guarantees=SYNTHETIC_CAT_M_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           store_groups=False, xes=False),
    Config(efficient=False, guarantees=SYNTHETIC_NUM_AM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           store_groups=False, xes=False),
    Config(efficient=False, guarantees=SYNTHETIC_NUM_M_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           store_groups=False, xes=False),
    Config(efficient=False, guarantees=SYNTHETIC_NUM_NM_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           store_groups=False, xes=False),
    Config(efficient=False, guarantees=SYNTHETIC_K_GROUPS_GUARANTEE, distance_notion=INTER_GROUP_INTERLEAVING,
           greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
           store_groups=False, xes=False)
]


class ConstraintTestCase(unittest.TestCase):

    def setUp(self):
        self.event_log = from_pm4py_event_log(read_basic_pm4py("../"+SYNTHETIC_LOGS_DIR, "default_tree_119999493402419830.xes"), "test")

    def test_anti_monotone_categorical(self):
        print("test_anti_monotone_categorical")
        abstract_log(self.event_log, _configs_basic[0])

    def test_anti_monotone_numeric(self):
        print("test_anti_monotone_numeric")
        abstract_log(self.event_log, _configs_basic[2])

    def test_monotone_categorical(self):
        print("test_monotone_categorical")
        abstract_log(self.event_log, _configs_basic[1])

    def test_monotone_numeric(self):
        print("test_monotone_numeric")
        abstract_log(self.event_log, _configs_basic[3])

    def test_non_monotone_numeric(self):
        print("test_non_monotone_numeric")
        abstract_log(self.event_log, _configs_basic[4])

    def test_grouping_constraint(self):
        print("test_size_of_grouping")
        abstract_log(self.event_log, _configs_basic[5])
