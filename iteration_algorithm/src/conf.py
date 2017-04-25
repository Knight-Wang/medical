#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: sunmeng(sunmeng94@163.com)

相关配置
"""
import os

#各种路径
CURRENT_DIR = os.path.abspath("%s/../" % __file__)
DATA_DIR = os.path.join(CURRENT_DIR, "../data")

RECORDS_FILE = os.path.join(DATA_DIR, "records.txt")
PREPROCESS_RESULT_FILE = os.path.join(DATA_DIR, "preprocess_result.bin")
DICT_FILE = os.path.join(DATA_DIR, "i2025.txt")
NETWORK_FILE = os.path.join(DATA_DIR, "network.bin")
TEST_FILE = os.path.join(DATA_DIR, "test.txt")

#参与消歧的疾病范围(I20-I25开头)
FILTER_PREFIX = ["I20", "I21", "I22", "I23", "I24", "I25"]

#用于训练疾病网络的记录条数
NUM_TRAIN = 100000

#网络迭代次数
NUM_ITERATION = 5

#实体流行度popSim与文本相似度localSim的权重参数
POPSIM_FACTOR = 1.2

#PageRank迭代次数
PPR_ITERATION_TIMES = 20

#PageRank跳转概率
PPR_JUMP_PROB = 0.2

