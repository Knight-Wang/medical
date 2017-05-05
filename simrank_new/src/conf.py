#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

CURRENT_DIR = os.path.abspath("%s/../" % __file__)
DATA_DIR = os.path.join(CURRENT_DIR, "../data")

RECORDS_FILE = os.path.join(DATA_DIR, "records.txt")
DICT_FILE = os.path.join(DATA_DIR, "i2025.txt")
TEST_FILE = os.path.join(DATA_DIR, "test.txt")

FILTER_PREFIX = ["I20", "I21", "I22", "I23", "I24", "I25"]
NUM_TRAIN = 100000
NUM_ITERATION = 10

THRESHOLD = 0.85

FACTOR_C = 0.8

NETWORK_FILE = os.path.join(DATA_DIR, "network.bin")
NAME_DICT_FILE = os.path.join(DATA_DIR, "name_dict.bin")
INIT_RES = os.path.join(DATA_DIR, "init_res.bin")
NO_CAND = os.path.join(DATA_DIR, "no_cand.bin")
