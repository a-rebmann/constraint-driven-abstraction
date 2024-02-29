from const import time_out, MAX

full_result_header_reduced = ["config",
                              "avg best solution",
                              "avg candidates found",
                              "avg num input event classes",
                              "avg num output classes",
                              "avg total runtime",
                              "dfg_density_in",
                              "size reduction",
                              "cfc_in_bpmn",
                              "cfc_out_bpmn",
                              "complexity ratio",
                              "silhouette",
                              "reached_timeout"
                              ,"solved"
                              ]

single_result_header = ["config",
                        "log",
                        "best solution",
                        "time s1",
                        "time s2",
                        "time s3",
                        "candidates found",
                        "num input classes",
                        "num output classes",
                        "total runtime",
                        "dfg_density_in",
                        "size reduction",
                        "cfc_in_bpmn",
                        "cfc_out_bpmn",
                        "complexity reduction",
                        "silhouette coefficient",
                        "reached_timeout"
                        ,"solved"
                        ]


class EvaluationResult:

    def __init__(self, setting, config):
        self.setting = setting
        self.config = config
        self.step1_time = 0
        self.step2_time = 0
        self.step3_time = 0
        self.best_solution = float("inf")
        self.num_candidates = 0
        self.eval_log = ""
        self.num_event_classes = 0
        self.num_cases = 0
        self.num_output_event_cases = 0
        self.original_log_location = ""
        self.abstracted_log_location = ""
        self.abstracted_log_name = ""
        self.dfg_density_in = 1
        self.dfg_density_out = 1
        self.dfg_diameter_in = float("inf")
        self.dfg_diameter_out = float("inf")
        self.cfc_in = 0
        self.cfc_out = 0
        self.avg_conn_degree_in = 0
        self.avg_conn_degree_out = 0
        self.cfc_in_bpmn = 1
        self.cfc_out_bpmn = 1
        self.avg_conn_degree_in_bpmn = 0
        self.avg_conn_degree_out_bpmn = 0
        self.silhouette_ours = 0
        self.silhouette_inf_dfc = 0
        self.reached_timeout = False
        self.reached_end_size = False
        self.solution = []
        self.behavioral_conf = 0

    def get_simple_results(self):
        res = [str(self.config),
               self.eval_log,
               self.best_solution]
        res = res + [self.step1_time if self.step1_time < time_out else time_out]
        res = res + [self.step2_time]
        res = res + [self.step3_time]
        res = res + [self.num_candidates]
        res = res + [self.num_event_classes]
        res = res + [self.num_output_event_cases]
        res = res + [sum(res[3:5])]
        res = res + [self.dfg_density_in]
        res = res + [self.num_output_event_cases/self.num_event_classes]
        res = res + [self.cfc_in_bpmn]
        res = res + [self.cfc_out_bpmn]
        if self.cfc_in_bpmn > 0:
            res = res + [1 if self.cfc_out_bpmn == self.cfc_in_bpmn else (self.cfc_out_bpmn / self.cfc_in_bpmn)]
        else:
            res = res + [1]
        res = res + [self.silhouette_ours]
        res = res + [self.reached_timeout or self.step1_time > time_out]
        #res = res + [self.reached_end_size]
        res = res + ["False" if len(self.solution) == 0 or self.num_candidates == 0 else "True"]
        return res


class FullResult:

    def __init__(self, setting: str, config):
        self.setting = setting
        self.config = config
        self.result_list = list()
        self.total_time = 0

    def get_aggregate_config_results_reduced(self, only_feasible=False):
        if only_feasible:
            result_list_to_consider = [result for result in self.result_list if len(result.solution) != 0 and result.num_candidates != 0]
            print(len(result_list_to_consider))
        else:
            result_list_to_consider = self.result_list
        if len(result_list_to_consider) < 1:
            return ""
        if only_feasible:
            res = [str(self.config),
                   sum([result.best_solution for result in result_list_to_consider]) / len(result_list_to_consider)]
            res_t = [
                sum([result.step1_time if result.step1_time < time_out else time_out for result in
                     result_list_to_consider]) / len(
                    result_list_to_consider)]
            res_t = res_t + [sum([result.step2_time for result in result_list_to_consider]) / len(result_list_to_consider)]
            res_t = res_t + [sum([result.step3_time for result in result_list_to_consider]) / len(result_list_to_consider)]
            res = res + [sum([result.num_candidates for result in result_list_to_consider]) / len(result_list_to_consider)]
            res = res + [sum([result.num_event_classes for result in result_list_to_consider]) / len(result_list_to_consider)]
            res = res + [sum([result.num_output_event_cases for result in result_list_to_consider]) / len(result_list_to_consider)]
            res = res + [sum(res_t)]
            res = res + [sum([result.dfg_density_in for result in result_list_to_consider]) / len(result_list_to_consider)]
            res = res + [1-(res[4] / res[3])]
            res = res + [sum([result.cfc_in_bpmn for result in result_list_to_consider if result.cfc_in_bpmn > 0]) / len(
                [1 for result in result_list_to_consider if result.cfc_in_bpmn > 0])]
            res = res + [sum([result.cfc_out_bpmn for result in result_list_to_consider if result.cfc_out_bpmn > 0]) / len(
                [1 for result in result_list_to_consider if result.cfc_out_bpmn > 0])]
            res = res + [1-sum(
                [1 if result.cfc_out_bpmn == result.cfc_in_bpmn else (result.cfc_out_bpmn / result.cfc_in_bpmn) for
                 result in result_list_to_consider if
                 result.cfc_in_bpmn > 0]) / len([1 for result in result_list_to_consider if result.cfc_in_bpmn > 0])]
            if len([1 for result in result_list_to_consider if result.silhouette_ours != "NaN"]) == 0:
                res = res + ["NaN"]
            else:
                res = res + [
                    sum([result.silhouette_ours for result in result_list_to_consider if
                         result.silhouette_ours != "NaN"]) / len(
                        [1 for result in result_list_to_consider if result.silhouette_ours != "NaN"])]
            res = res + [sum([result.reached_timeout or result.step1_time > time_out for result in result_list_to_consider])]
            res = res + [sum([0 if len(result.solution) == 0 or result.num_candidates == 0 else 1 for result in result_list_to_consider])]
        else:
            res = [str(self.config),
                   sum([result.best_solution for result in result_list_to_consider]) / len(result_list_to_consider)]
            res_t = [
                sum([result.step1_time if result.step1_time < time_out else time_out for result in result_list_to_consider]) / len(
                    result_list_to_consider)]
            res_t = res_t + [sum([result.step2_time for result in result_list_to_consider]) / len(result_list_to_consider)]
            res_t = res_t + [sum([result.step3_time for result in result_list_to_consider]) / len(result_list_to_consider)]
            res = res + [sum([result.num_candidates for result in result_list_to_consider]) / len(result_list_to_consider)]
            res = res + [sum([result.num_event_classes for result in result_list_to_consider]) / len(result_list_to_consider)]
            res = res + [sum([result.num_output_event_cases for result in result_list_to_consider]) / len(result_list_to_consider)]
            res = res + [sum(res_t)]
            res = res + [sum([result.dfg_density_in for result in result_list_to_consider]) / len(result_list_to_consider)]
            res = res + [1-(res[4] / res[3])]
            if all(result.cfc_in_bpmn == 0 for result in result_list_to_consider):
                res = res + [1]
            else:
                res = res + [sum([result.cfc_in_bpmn for result in result_list_to_consider if result.cfc_in_bpmn > 0]) / len([1 for result in result_list_to_consider if result.cfc_in_bpmn > 0])]
            if all(result.cfc_out_bpmn == 0 for result in result_list_to_consider):
                res = res + [1]
            else:
                res = res + [sum([result.cfc_out_bpmn for result in result_list_to_consider if result.cfc_out_bpmn > 0]) / len([1 for result in result_list_to_consider if result.cfc_out_bpmn > 0])]
            if all(result.cfc_in_bpmn == 0 for result in result_list_to_consider):
                res = res + [1]
            else:
                res = res + [1-sum(
                    [1 if result.cfc_out_bpmn == result.cfc_in_bpmn else (result.cfc_out_bpmn / result.cfc_in_bpmn) for result in result_list_to_consider if
                     result.cfc_in_bpmn > 0]) / len([1 for result in result_list_to_consider if result.cfc_in_bpmn > 0])]
            if len([1 for result in result_list_to_consider if result.silhouette_ours != "NaN"]) == 0:
                res = res + ["NaN"]
            else:
                res = res + [
                    sum([result.silhouette_ours for result in result_list_to_consider if result.silhouette_ours != "NaN"]) / len(
                        [1 for result in result_list_to_consider if result.silhouette_ours != "NaN"])]
            res = res + [sum([result.reached_timeout or result.step1_time > time_out for result in result_list_to_consider])]
            res = res + [sum([0 if len(result.solution) == 0 or result.num_candidates == 0 else 1 for result in result_list_to_consider])]
        return res
