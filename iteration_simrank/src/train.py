#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: sunmeng(sunmeng94@163.com)
"""
import copy
import cPickle as pickle
import sys


import candidate_generator
from conf import *
from processor import *
from test import *


def in_range(icd):
    for prefix in FILTER_PREFIX:
        if icd.startswith(prefix):
            return True
    return False


if __name__ == "__main__":
    origin_records = []
    for i, line in enumerate(open(RECORDS_FILE, "r")):
        data = line.rstrip("\n").decode("UTF-8").split("\t")
        record = {}
        record["main"] = []
        icd, name = data[0].split("##")
        if in_range(icd):
            record["main"].append(name)
        record["other"] = []
        for j in range(1, len(data)):
            icd, name = data[j].split("##")
            if in_range(icd):
                record["other"].append(name)
        origin_records.append(record)
        total = len(record["main"]) + len(record["other"])
    
    try:
        print >> sys.stderr, 'Loading preprocess result...'
        with open(PREPROCESS_RESULT_FILE, 'rb') as data_file:
            preprocessed_records = pickle.load(data_file)
    except:
        print >> sys.stderr, 'Failed to load'
        print >> sys.stderr, 'Preprocessing...'
        preprocessed_records = []
        for i, record in enumerate(origin_records):
            if (i >= NUM_TRAIN):
                break                    
            preprocessed_record = process_record(record)
            preprocessed_records.append(preprocessed_record)
        with open(PREPROCESS_RESULT_FILE, 'wb') as data_file:
            pickle.dump(preprocessed_records, data_file, True)
    
    tester = Tester()
    processor = Processor()
    tester.test(processor, "nonetwork")
    network = Network(preprocessed_records)
    processor.set_network(network)
    for i in range(NUM_ITERATION):
        print "---------- Iteration %d ----------" % i
        processor.simrank()  # 使用simrank算法得到任意两点之间的相似度
        # print processor.sim_matrix
        tester.test(processor, str(i))
        for j, preprocessed_record in enumerate(preprocessed_records):
            preprocessed_records[j] = processor.disambiguate_simrank(origin_records[j], preprocessed_record)
        network = Network(preprocessed_records)
        processor.set_network(network)
        processor.save_network()
