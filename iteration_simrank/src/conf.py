#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: sunmeng(sunmeng94@163.com)
"""
import os

CURRENT_DIR = os.path.abspath("%s/../" % __file__)
DATA_DIR = os.path.join(CURRENT_DIR, "../data")

RECORDS_FILE = os.path.join(DATA_DIR, "records.txt")
PREPROCESS_RESULT_FILE = os.path.join(DATA_DIR, "preprocess_result.bin")
DICT_FILE = os.path.join(DATA_DIR, "i2025.txt")
NETWORK_FILE = os.path.join(DATA_DIR, "network.bin")
TEST_FILE = os.path.join(DATA_DIR, "test.txt")

FILTER_PREFIX = ["I20", "I21", "I22", "I23", "I24", "I25"]
NUM_TRAIN = 100000
NUM_ITERATION = 5

POPSIM_FACTOR = 1
PPR_ITERATION_TIMES = 20
PPR_JUMP_PROB = 0.2

SIMRANK_DAMP = 0.8
SIMRANK_ITERATION_TIMES = 100
SIMRANK_FACTOR = 0.5

