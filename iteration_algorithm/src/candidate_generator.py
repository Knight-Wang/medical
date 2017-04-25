#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: sunmeng(sunmeng94@163.com)

封装候选实体选取算法
"""
import os
import sys

sys.path.append(os.path.abspath("%s/../../.." % __file__))
from Preprocess import *

DICT_FILE = "../data/i2025.txt"

#类似cache，记录每个非标准名称的候选实体选取结果，当再次出现相同的非标准名称时，直接返回结果，避免重复计算
candidate_cache = {}

#载入字典
disease_dict = {}
loop = 0
for line in open(DICT_FILE, "r"):
    loop += 1
    if loop == 1:
        continue
    data = line.rstrip("\n").decode("UTF-8").split("\t")
    disease_dict[data[1]] = data[0]


def generate_candidate(mention):
    """
    产生候选实体
    """
    if mention in candidate_cache:
        return candidate_cache[mention]
    p_name = process(mention)
    name_dict, match_type = getMappingResult(p_name, disease_dict, {})
    candidate_cache[mention] = sorted(name_dict.iteritems(), key=lambda x: x[1], reverse=True)
    return candidate_cache[mention]
