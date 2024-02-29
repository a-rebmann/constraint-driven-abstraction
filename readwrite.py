from pm4py.objects.log.importer.xes import importer as importer
from pm4py.objects.log.util import dataframe_utils
from pm4py.objects.conversion.log import converter
from pm4py.objects.conversion.bpmn import converter as bpmn_converter

from const import XES_NAME, XES_TIME, XES_CASE
import pickle
import pandas as pd
import pm4py
import os
from eval.config import Config
from model.pm.log import Log


def load_precomputed(log, config):
    groups = deserialize_groups(log, config)
    dist_map = deserialize_dist_map(log, config)
    return groups, dist_map


def store_precomputed(log: Log, config: Config, groups, dist_map):
    serialize_groups(log, config, groups)
    serialize_dist_map(log, config, dist_map)


def read(path, log_file, keys, labels, timestamp, as_df=False):
    df = None
    if log_file.endswith('.csv'):
        try:
            df = pd.read_csv(os.path.join(path, log_file), sep=';')
        except UnicodeDecodeError:
            df = pd.read_csv(os.path.join(path, log_file), sep=';', encoding="ISO-8859-1")
        try:
            df = dataframe_utils.convert_timestamp_columns_in_df(df)
        except TypeError:
            print('conversion of timestamps failed')
            pass
        if log_file in labels:
            df.rename(columns={labels[log_file]: XES_NAME}, inplace=True)
        if log_file in timestamp:
            df.rename(columns={timestamp[log_file]: XES_TIME}, inplace=True)
        log = convert_df_to_log(df, log_file, keys)
    else:
        log = importer.apply(os.path.join(path, log_file))
    if as_df:
        df = converter.apply(log, variant=converter.Variants.TO_DATA_FRAME)
    return log, df


def read_basic_pm4py(path, log_file):
    return importer.apply(os.path.join(path, log_file))


def convert_df_to_log(df, filename, log_keys, standard=False):
    if standard:
        parameters = {converter.Variants.TO_EVENT_LOG.value.Parameters.CASE_ID_KEY: XES_CASE}
        return converter.apply(df, parameters=parameters, variant=converter.Variants.TO_EVENT_LOG)
    if filename in log_keys:
        return converter.apply(df, parameters={converter.to_event_log.Parameters.CASE_ID_KEY: log_keys[filename]},
                               variant=converter.Variants.TO_EVENT_LOG)
    return converter.apply(df, variant=converter.Variants.TO_EVENT_LOG)


def serialize_event_log(path, log):
    with open(os.path.join(path, log.name + '.pkl'), 'wb') as f:
        pickle.dump(log, f)


def serialize_groups(log: Log, config: Config, groups):
    with open(os.path.join(config.group_ser_path, log.name + str(config) + "_groups.pkl"),
              'wb') as f:
        pickle.dump(groups, f)


def deserialize_groups(log: Log, config: Config):
    try:
        with open(os.path.join(config.group_ser_path, log.name + str(config) + "_groups.pkl"), 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return False


def serialize_dist_map(log: Log, config: Config, dist_map):
    with open(os.path.join(config.group_ser_path, log.name + str(config) + "_dist_map.pkl"),
              'wb') as f:
        pickle.dump(dist_map, f)


def deserialize_dist_map(log: Log, config: Config):
    try:
        with open(os.path.join(config.group_ser_path, log.name + str(config) + "_dist_map.pkl"), 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return {}


def deserialize_event_log(path, name):
    try:
        with open(os.path.join(path, name + '.pkl'), 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return False


def write_xes(path, name, log):
    from pm4py.objects.log.exporter.xes import exporter as xes_exporter
    xes_exporter.apply(log, os.path.join(path, name + '.xes'))


def get_bpmn(path_to_bpmn, as_petri_net=True):
    bpmn_graph = pm4py.read_bpmn(path_to_bpmn)
    if as_petri_net:
        return bpmn_converter.apply(bpmn_graph)
    else:
        return bpmn_graph


def get_n_logs(path, n=1, name=None):
    if name:
        return {name: path}
    list_of_files = {}
    counter = 0
    for (dir_path, dir_names, filenames) in os.walk(path):
        for filename in filenames:
            if filename.endswith('.xes') or filename.endswith('.csv'):
                list_of_files[filename] = os.sep.join([dir_path])
                counter += 1
                if counter == n:
                    return list_of_files


def replace_char_seqs_in_file(path_to_file, char_seqs_to_replace, replacements):
    # read input file
    fin = open(path_to_file, "rt")
    # read file contents to string
    data = fin.read()
    # replace all occurrences of the required strings
    for char_seq_to_replace, replacement in zip(char_seqs_to_replace, replacements):
        data = data.replace(char_seq_to_replace, replacement)
    # close the input file
    fin.close()
    # open the input file in write mode
    fin = open(path_to_file, "wt")
    # overrite the input file with the resulting data
    fin.write(data)
    # close the file
    fin.close()
