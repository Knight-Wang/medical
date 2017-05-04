#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import networkx as nx
import cPickle

sys.path.append(os.path.abspath("%s/../../.." % __file__))
from Preprocess import *
from conf import *

DICT_FILE = "../data/i2025.txt"
disease_dict = {}
candidate_cache = {}
init_res = {}  # 初始相似度较高的
no_cand = set()  # 没有候选的非标准疾病名称集合
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
    candidate_cache[mention] = sorted(name_dict.iteritems(), key=lambda x: x[1], reverse=True)
    return candidate_cache[mention]


def in_range(icd):
    for prefix in FILTER_PREFIX:
        if icd.startswith(prefix):
            return True
    return False


def generate_network():
    """ 从原始数据中构建伴病网络
    :return: 构建好的伴病网络 networkx 实现
    """
    G = nx.Graph()  # 使用 networkx 中的无向图
    for i, line in enumerate(open(RECORDS_FILE, "r")):
        if i > NUM_TRAIN:  # 达到预设的训练数据条数，break
            break
        if not (i % 1000):
            print "第 %d 条记录" % i
        data = line.rstrip("\n").decode("UTF-8").split("\t")
        name_list = []  # 这条记录中的疾病名称
        for j in range(0, len(data)):
            icd, name = data[j].split("##")
            if not in_range(icd):  # 不是心脏病
                continue
            if name in disease_dict:  # 是标准疾病名称
                G.add_node(name, type=1)
                name_list.append(name)
            else:  # 非标准疾病名称
                can_list = generate_candidate(name)
                if not len(can_list):  # 没有候选，添加default名称
                    can_list = [(u'急性心肌梗死', 0.0)]
                    no_cand.add(name)  # 将没有候选的非标准疾病名称加入no_cand集合
                if can_list[0][1] > THRESHOLD:  # 相似度大于阈值
                    G.add_node(can_list[0][0], type=1)
                    if name not in init_res:
                        init_res[name] = can_list[0][0]
                    name_list.append(can_list[0][0])
                else:  # 相似度小于阈值，消歧的对象
                    G.add_node(name, type=0)
                    name_list.append(name)
        for p, np in enumerate(name_list):  # 添加疾病之间的边
            for q, nq in enumerate(name_list):
                if p >= q:
                    continue
                if G.has_edge(np, nq):  # ni, nj有边，调整权值
                    G[np][nq]["weight"] += 1
                else:  # ni, nj之间没有边，加边
                    G.add_edge(np, nq, weight=1)

    # 把没出现过的标准疾病名称加入到G中，方便后续操作
    for n_name in disease_dict:
        if not G.has_node(n_name):
            G.add_node(n_name, type=1)

    return G


G = generate_network()
print "节点数 %d " % len(G.nodes())
print "边数 %d" % len(G.edges())

print "非标准疾病名称 %d" % len(candidate_cache)

with open(NETWORK_FILE, "wb") as data_file:
    cPickle.dump(G, data_file, True)
with open(NAME_DICT_FILE, "wb") as data_file:
    cPickle.dump(candidate_cache, data_file, True)
with open(INIT_RES, "wb") as data_file:
    cPickle.dump(init_res, data_file, True)
with open(NO_CAND, "wb") as data_file:
    cPickle.dump(no_cand, data_file, True)
