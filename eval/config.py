import sys

from const import DEFAULT_LOG_SER_PATH, DEFAULT_GROUP_SER_PATH, DEFAULT_ABSTRACTED_PATH, SYNTHETIC_LOGS_DIR


class Config:

    def __init__(self, efficient, guarantees, distance_notion, greedy, handle_loops, handle_xor,
                 handle_concurrent, beam_size=1000, optimal_solution=True, create_mapping=True, do_projection=True,
                 only_complete=False, xes=True, store_groups=True, log_ser_path=DEFAULT_LOG_SER_PATH,
                 group_ser_path=DEFAULT_GROUP_SER_PATH, original_log_path=SYNTHETIC_LOGS_DIR,
                 abstracted_path=DEFAULT_ABSTRACTED_PATH, frac_to_hold=1.0):
        self.efficient = efficient
        self.guarantees = guarantees
        self.distance_notion = distance_notion
        self.greedy = greedy
        self.handle_loops = handle_loops
        self.handle_xor = handle_xor
        self.handle_concurrent = handle_concurrent
        self.beam_size = beam_size
        self.optimal_solution = optimal_solution
        self.create_mapping = create_mapping
        self.do_projection = do_projection
        self.only_complete = only_complete
        self.export_xes = xes
        self.store_groups = store_groups
        self.log_ser_path = log_ser_path
        self.group_ser_path = group_ser_path
        self.original_log_path = original_log_path
        self.abstracted_path = abstracted_path
        self.frac_to_hold = frac_to_hold

    def __repr__(self) -> str:
        res = ""
        res = res + "-".join(
                [str(constraint[0]) + "-" + str(constraint[1]) + "-" + str(constraint[2]) + "-" + str(constraint[3]) for constraint in self.guarantees])
        if self.frac_to_hold<1.0:
            res = res + "-" + str(self.frac_to_hold) + "-"
        if self.efficient:
            res = res + "-efficient-"
            if self.beam_size != sys.maxsize:
                res = res + "b=" +str(self.beam_size)
        else:
            res = res + "-basic-"
        if self.greedy:
            res = res + "greedy-"
        if self.handle_xor:
            res = res + "xor-"
        if self.handle_loops:
            res = res + "loops-"
        if self.handle_concurrent:
            res = res + "concurrent"
        res = res.replace(":", "-")
        return res
