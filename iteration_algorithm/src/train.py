#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: sunmeng(sunmeng94@163.com)

使用原始数据构建疾病网络，并利用消歧结果不断迭代
"""
import copy
import cPickle as pickle
import sys


import candidate_generator
from conf import *
from processor import *
from test import *


def in_range(icd):
    """
    该疾病是否在消歧范围内
    """
    for prefix in FILTER_PREFIX:
        if icd.startswith(prefix):
            return True
    return False


if __name__ == "__main__":
    #读取原始数据
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
    
    #读取原始数据的候选实体选取结果
    #候选实体选取速度较慢，因此在处理完后把结果记录到了文件中，每次直接读取文件即可。读取失败才会重新跑一遍。
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

    #测试候选实体选取top1准确率
    print "---------- No Network ----------"
    tester.test(processor, "nonetwork")

    #使用候选实体选取top1构建疾病网络
    network = Network(preprocessed_records)
    processor.set_network(network)

    #测试初始疾病网络消歧准确率
    print "---------- Origin Network ----------"
    tester.test(processor, str(0))

    #迭代更新疾病网络
    for i in range(NUM_ITERATION):
        print "---------- Iteration %d ----------" % (i + 1)
        new_records = []
        for j, preprocessed_record in enumerate(preprocessed_records):
            new_records.append(processor.disambiguate(origin_records[j], preprocessed_record))
        network = Network(new_records)
        processor.set_network(network)
        processor.save_network()
        tester.test(processor, str(i + 1))
