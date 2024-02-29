import sys
import unittest

from eval.config import Config
from evaluation_synthetic import get_synthetic_logs
from pm4py.simulation.playout import simulator
from main import read, from_pm4py_event_log, abstract_log
from const import *
from eval.discovery import dfg
from pm4py.objects.petri.petrinet import PetriNet, Marking
from pm4py.objects.petri import utils


def get_complete_net():
    net = PetriNet("new_petri_net")
    # creating source, p_1 and sink place
    source = PetriNet.Place("source")
    sink = PetriNet.Place("sink")
    p_1 = PetriNet.Place("p_A")
    p_2 = PetriNet.Place("p_B")
    p_3 = PetriNet.Place("p_C")
    p_4 = PetriNet.Place("p_D")
    p_5 = PetriNet.Place("p_E")

    p_6 = PetriNet.Place("p_Ao")
    p_7 = PetriNet.Place("p_Bo")
    p_8 = PetriNet.Place("p_Co")
    p_9 = PetriNet.Place("p_Do")
    p_10 = PetriNet.Place("p_Eo")

    # add the places to the Petri Net
    net.places.add(source)
    net.places.add(sink)
    net.places.add(p_1)
    net.places.add(p_2)
    net.places.add(p_3)
    net.places.add(p_4)
    net.places.add(p_5)
    net.places.add(p_6)
    net.places.add(p_7)
    net.places.add(p_8)
    net.places.add(p_9)
    net.places.add(p_10)

    # Create transitions
    t_1 = PetriNet.Transition("split", None)
    t_2 = PetriNet.Transition("join", None)

    t_3 = PetriNet.Transition("A", "A")
    t_4 = PetriNet.Transition("B", "B")
    t_5 = PetriNet.Transition("C", "C")
    t_6 = PetriNet.Transition("D", "D")
    t_7 = PetriNet.Transition("E", "E")

    # Add the transitions to the Petri Net
    net.transitions.add(t_1)
    net.transitions.add(t_2)
    net.transitions.add(t_3)
    net.transitions.add(t_4)
    net.transitions.add(t_5)
    net.transitions.add(t_6)
    net.transitions.add(t_7)

    utils.add_arc_from_to(source, t_1, net)

    utils.add_arc_from_to(t_1, p_1, net)
    utils.add_arc_from_to(t_1, p_2, net)
    utils.add_arc_from_to(t_1, p_3, net)
    utils.add_arc_from_to(t_1, p_4, net)
    utils.add_arc_from_to(t_1, p_5, net)

    utils.add_arc_from_to(p_1, t_3, net)
    utils.add_arc_from_to(p_2, t_4, net)
    utils.add_arc_from_to(p_3, t_5, net)
    utils.add_arc_from_to(p_4, t_6, net)
    utils.add_arc_from_to(p_5, t_7, net)

    utils.add_arc_from_to(t_3, p_6, net)
    utils.add_arc_from_to(t_4, p_7, net)
    utils.add_arc_from_to(t_5, p_8, net)
    utils.add_arc_from_to(t_6, p_9, net)
    utils.add_arc_from_to(t_7, p_10, net)

    utils.add_arc_from_to(p_6, t_2, net)
    utils.add_arc_from_to(p_7, t_2, net)
    utils.add_arc_from_to(p_8, t_2, net)
    utils.add_arc_from_to(p_9, t_2, net)
    utils.add_arc_from_to(p_10, t_2, net)

    utils.add_arc_from_to(t_2, sink, net)

    initial_marking = Marking()
    initial_marking[source] = 1
    return net, initial_marking


class ConstraintTestCase(unittest.TestCase):

    config = Config(efficient=False, guarantees=[], distance_notion=INTER_GROUP_INTERLEAVING,
                    greedy=False, beam_size=sys.maxsize, handle_loops=True, handle_xor=True, handle_concurrent=True,
                    store_groups=False, xes=False)

    def setUp(self):
        net, initial_marking = get_complete_net()

        simulated_log = simulator.apply(net, initial_marking, variant=simulator.Variants.EXTENSIVE,
                                        parameters={simulator.Variants.EXTENSIVE.value.Parameters.MAX_TRACE_LENGTH: 7})
        print(len(simulated_log), " traces")
        self.event_log = from_pm4py_event_log(simulated_log, "dfg_complete")
        dfg(self.event_log.pm4py, viz=True)

    def test_anti_monotone_categorical(self):
        print("test_exclusive")
        abstract_log(self.event_log, self.config)
