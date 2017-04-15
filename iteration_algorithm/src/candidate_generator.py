#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: sunmeng(sunmeng94@163.com)
"""
import os
import sys

sys.path.append(os.path.abspath("%s/../../.." % __file__))
from Preprocess import *

DICT_FILE = "../data/i2025.txt"
disease_dict = {}
candidate_cache = {}
loop = 0
for line in open(DICT_FILE, "r"):
    loop += 1
    if loop == 1:
        continue
    data = line.rstrip("\n").decode("UTF-8").split("\t")
    disease_dict[data[1]] = data[0]


def generate_candidate(mention):
    if mention in candidate_cache:
        return candidate_cache[mention]
    p_name = process(mention)
    name_dict, match_type = getMappingResult(p_name, disease_dict, {})
    candidate_cache[mention] = sorted(name_dict.iteritems(), key=lambda x: x[1], reverse =  True)
    return candidate_cache[mention]


def predict(mention):
    p_name = process(mention)
    name_dict, match_type = getMappingResult(p_name, disease_dict)
    entity_list = []
    best_score = -1
    for key in name_dict:
        if name_dict[key] > best_score:
            best_score = name_dict[key]
            entity_list = [key]
        elif name_dict[key] == best_score:
            entity_list.append(key)
    return entity_list

