import logging
import sys

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from const import XES_RESOURCE, EXACTLY, INTER_GROUP_INTERLEAVING, IN_PATH, CL, XES_NAME
from eval.config import Config
from main import prepare_single_log
from model.pm.log import Log
from optimization.sim.simfunction import group_wise_interleaving_variants
from readwrite import deserialize_event_log


class App:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        # Don't forget to close the driver connection when you are finished with it
        self.driver.close()

    @staticmethod
    def _create_and_return_df_relation(tx, from_ec, to_ec, log, att_for_gq, att_val_l, att_val_r):
        from_ec_name = log.unique_event_classes[from_ec]
        from_ec_count = log.activity_counts[from_ec_name]
        to_ec_name = log.unique_event_classes[to_ec]
        to_ec_count = log.activity_counts[to_ec_name]
        df_count = log.dfg_dict[(from_ec_name, to_ec_name)]
        query = (
                "MERGE (e1:EventClass {num: $from_ec, name: $from_ec_name, count: $from_ec_count" + (
            ", " + att_for_gq + ": $att_val_l" if att_for_gq is not None else "") + "})"
                                                                                    "MERGE (e2:EventClass {num: $to_ec, name: $to_ec_name, count: $to_ec_count" + (
                    ", " + att_for_gq + ": $att_val_r" if att_for_gq is not None else "") + "})"
                                                                                            "MERGE (e1)-[:followed_by {df_count:$df_count}]->(e2) "
                                                                                            "RETURN e1, e2"
        )
        result = tx.run(query, from_ec=from_ec, to_ec=to_ec, from_ec_name=from_ec_name, to_ec_name=to_ec_name,
                        from_ec_count=from_ec_count, to_ec_count=to_ec_count, att_val_l=att_val_l, att_val_r=att_val_r,
                        df_count=df_count)
        try:
            return [{"e1": record["e1"]["name"], "e2": record["e2"]["name"]}
                    for record in result]
        # Capture any errors along with the query and data for traceability
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=query, exception=exception))
            raise

    def create_dfg(self, log: Log, att_for_gq):
        ec_to_att = dict()
        if att_for_gq is not None:
            for ec in log.unique_event_classes:
                vals = log.get_att_vals_for_ec[ec][att_for_gq]
                if len(vals) == 1:
                    ec_to_att[ec] = vals[0]
                else:
                    ec_to_att[ec] = ""
            if ":" in att_for_gq:
                att_for_gq = att_for_gq.replace(":", "")
            if "(" in att_for_gq:
                att_for_gq = att_for_gq.replace("(", "")
            if ")" in att_for_gq:
                att_for_gq = att_for_gq.replace(")", "")
        with self.driver.session() as session:
            att_val_l, att_val_r = None, None
            for item in log.dfg_dict.keys():
                if item[0] in ec_to_att.keys() and item[1] in ec_to_att.keys():
                    att_val_l, att_val_r = ec_to_att[item[0]], ec_to_att[item[1]]
                result = session.write_transaction(
                    self._create_and_return_df_relation, log.unique_event_classes.index(item[0]),
                    log.unique_event_classes.index(item[1]), log, att_for_gq, att_val_l, att_val_r)
                # for record in result:
                #     print("Add directly-follows relation between: {e1}, {e2}".format(
                #         e1=record['e1'], e2=record['e2']))

    @staticmethod
    def _query_depth(tx, max_depth, n, class_constraint):
        # query = "MATCH (me)-[:followed_by*" + str(max_depth) + "]->(remote_friend) WITH count(DISTINCT remote_friend) AS rfs WHERE me.name = '" + str(n) + "' AND rfs < " + str(max_depth) + " RETURN DISTINCT remote_friend"
        # query = "MATCH (me)-[:followed_by*" + str(
        #     max_depth) + "]->(remote_friend) WITH me, remote_friend, count(DISTINCT remote_friend) AS rfs WHERE me.name = '" + str(
        #     n) + "' AND rfs < " + str(class_constraint) + " RETURN DISTINCT remote_friend"
        num_class_query = "MATCH (me)-[:followed_by*" + str(
            max_depth) + "]->(remote_friend) WHERE me.name = '" + str(
            n) + "' RETURN DISTINCT remote_friend LIMIT " + str(
            class_constraint)
        # print(num_class_query)
        result = tx.run(num_class_query)
        try:
            return [{"num": record["remote_friend"]["num"], "name": record["remote_friend"]["name"]} for record in
                    result]
        # Capture any errors along with the query and data for traceability
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=num_class_query, exception=exception))
            raise

    @staticmethod
    def _query_cannot_link(tx, max_depth, n, class_constraint, c=[]):
        cannot_link_query = "MATCH (me)-[:followed_by*" + str(
            max_depth) + "]->(remote_friend) WHERE me.name = '" + str(
            n) + "'" + " ".join([" and remote_friend.name <> '" + clc[1] + "'" for clc in c if
                                 clc[0] == str(n)]) + " RETURN DISTINCT remote_friend LIMIT " + str(
            class_constraint)
        # print(cannot_link_query)
        result = tx.run(cannot_link_query)
        try:
            return [{"num": record["remote_friend"]["num"], "name": record["remote_friend"]["name"]} for record in
                    result]
        # Capture any errors along with the query and data for traceability
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=cannot_link_query, exception=exception))
            raise

    @staticmethod
    def _query_class_att(tx, max_depth, n, class_constraint, att_name):
        if ":" in att_name:
            att_name = att_name.replace(":", "")
        class_att_query = "MATCH (me)-[:followed_by*" + str(
            max_depth) + "]->(remote_friend) WHERE me.name = '" + str(
            n) + "' AND me." + att_name + " = remote_friend." + att_name + " RETURN DISTINCT remote_friend LIMIT " + str(
            class_constraint)

        print(class_att_query)
        result = tx.run(class_att_query)
        try:
            return [{"num": record["remote_friend"]["num"], "name": record["remote_friend"]["name"]} for record in
                    result]
        # Capture any errors along with the query and data for traceability
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=class_att_query, exception=exception))
            raise

    @staticmethod
    def _query_must_link(tx, max_depth, n, class_constraint, m=[]):
        # TODO
        must_link_query = "MATCH (me)-[:followed_by*" + str(
            max_depth) + "]->(remote_friend) WHERE me.name = '" + str(
            n) + "' RETURN DISTINCT remote_friend LIMIT " + str(
            class_constraint)
        # print(must_link_query)
        result = tx.run(must_link_query)
        try:
            return [{"num": record["remote_friend"]["num"], "name": record["remote_friend"]["name"]} for record in
                    result]
        # Capture any errors along with the query and data for traceability
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=must_link_query, exception=exception))
            raise

    def query_depth(self, max_depth, n, class_constraint):
        with self.driver.session() as session:
            result = session.write_transaction(
                self._query_depth, max_depth=max_depth, n=n, class_constraint=class_constraint)
            return [res["num"] for res in result]

    def query_cl(self, max_depth, n, class_constraint, c):
        with self.driver.session() as session:
            result = session.write_transaction(
                self._query_cannot_link, max_depth=max_depth, n=n, class_constraint=class_constraint, c=c)
            return [res["num"] for res in result]

    def query_att_class(self, max_depth, n, class_constraint, att):
        with self.driver.session() as session:
            result = session.write_transaction(
                self._query_class_att, max_depth=max_depth, n=n, class_constraint=class_constraint, att_name=att)
            return [res["num"] for res in result]

    @staticmethod
    def _delete_node(tx, node_name):
        query = "MATCH (n {name: '" + node_name + "'}) DETACH DELETE n"
        tx.run(query, name=node_name)

    def delete_dfg(self, log):
        for node in log.unique_event_classes:
            with self.driver.session() as session:
                session.write_transaction(
                    self._delete_node, node_name=node)


def get_candidates(log, guarantees, att_for_gq=None):
    scheme = "neo4j"  # Connecting to Aura, use the "neo4j+s" URI scheme
    host_name = "localhost"
    port = 7687
    url = "{scheme}://{host_name}:{port}".format(scheme=scheme, host_name=host_name, port=port)
    user = "neo4j"
    password = "123qwe"
    app = App(url, user, password)
    app.create_dfg(log, att_for_gq)
    candidates = set()
    dist_map = {}
    for n in log.unique_event_classes:
        print(n)
        for i, n2 in enumerate(log.unique_event_classes):
            if i == guarantees[0][3]:
                break
            if guarantees[0][0] == XES_NAME:
                candidate = frozenset(app.query_depth(max_depth=i, n=n, class_constraint=guarantees[0][3]))
                # print(candidate)
            # TODO randomly create cannot-link constraints
            elif guarantees[0][0] == CL:
                candidate = frozenset(
                    app.query_cl(max_depth=i, n=n, class_constraint=guarantees[0][3], c=guarantees[0][1]))
            else:
                candidate = frozenset(
                    app.query_att_class(max_depth=i, n=n, class_constraint=guarantees[0][3], att=guarantees[0][0]))
            group_dist, co_occurrence = group_wise_interleaving_variants(candidate, log, handle_loops=True,
                                                                         handle_xor=False,
                                                                         handle_concurrent=True)
            if len(candidate) > 0:
                if len(candidate) == 1:
                    dist_map[candidate] = 1.0
                else:
                    dist_map[candidate] = group_dist
                candidates.add(candidate)

    # print(dist_map)
    # print(candidates)
    app.delete_dfg(log)  # TODO handle with care
    app.close()
    return list(candidates), dist_map


RUNNING_EXAMPLE_CONSTRAINT = [(XES_RESOURCE, EXACTLY, None, 1)]

CONFIG = Config(efficient=True, guarantees=RUNNING_EXAMPLE_CONSTRAINT, distance_notion=INTER_GROUP_INTERLEAVING,
                greedy=False,
                optimal_solution=True,
                create_mapping=True, do_projection=True, only_complete=False, xes=True, handle_xor=True,
                handle_loops=True, handle_concurrent=True)

if __name__ == "__main__":
    event_log = deserialize_event_log("../" + CONFIG.log_ser_path, "runningexample")
    if not event_log:
        event_log = prepare_single_log("../" + IN_PATH, "dfcomplete.xes", "../" + CONFIG.log_ser_path)
    clcs = [("ckc", "ckt"), ("acc", "rej")]
    get_candidates(event_log, [(CL, clcs, 0, 10)])
    sys.exit(0)
