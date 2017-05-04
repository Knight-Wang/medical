#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import numpy as np

from test import *

name2id = {}
id2name = []


def init(G, name_dic):
    """
    :param G: 网络，networkx 实现
    :param can_dic: 字典，<key, value> = <非标准疾病名称, [(候选标名1, 相似度1), (候选标名2, 相似度2), ...]>
    :return: simrank 矩阵
    """
    n = len(G.nodes())
    for i, ni in enumerate(G.nodes()):
        name2id[ni] = i
        id2name.append(ni)
    sim_matrix = np.zeros([n, n])

    for u_name in name_dic:
        if u_name not in name2id:
            continue
        x = name2id[u_name]
        can_list = name_dic[u_name]
        for t in can_list:
            y = name2id[t[0]]
            sim_matrix[x, y] = sim_matrix[y, x] = t[1]

    for i in range(n):
        sim_matrix[i, i] = 1.0

    return sim_matrix


def iterate(G, sim_matrix):
    ret = sim_matrix
    for i, u in enumerate(G.nodes()):
        for j, v in enumerate(G.nodes()):
            total_sim = 0.0
            u_f = 0
            for un in G.neighbors(u):
                u_f += G[u][un]["weight"]
            v_f = 0
            for vn in G.neighbors(v):
                v_f += G[v][vn]["weight"]
            if not G.neighbors(u) or not G.neighbors(v):
                continue
            for un in G.neighbors(u):
                for vn in G.neighbors(v):
                    total_sim += G[u][un]["weight"] * G[v][vn]["weight"] * sim_matrix[name2id[un], name2id[vn]]
            total_sim *= FACTOR_C
            u_f *= v_f
            if u_f:
                total_sim /= u_f
                ret[i, j] = ret[j, i] = 0.2 * total_sim + 0.8 * sim_matrix[i, j]
    return ret


def load():
    with open(NETWORK_FILE, "rb") as data_file:
        G = cPickle.load(data_file)

    with open(NAME_DICT_FILE, "rb") as data_file:
        can_dic = cPickle.load(data_file)

    with open(INIT_RES, "rb") as data_file:
        init_res = cPickle.load(data_file)

    with open(NO_CAND, "rb") as data_file:
        no_cand = cPickle.load(data_file)

    return G, can_dic, init_res, no_cand


G, name_dic, init_res, no_cand = load()
print "初始结果："
test_init(name_dic, no_cand)

sim_matrix = init(G, name_dic)
for i in range(NUM_ITERATION):
    print >> sys.stderr, "ITERATION %d" % (i + 1)
    sim_matrix = iterate(G, sim_matrix)
    res = {}
    for j, nj in enumerate(G.nodes()):
        if G.node[nj]["type"] == 0:
            maxn = 0.0
            max_name = u""
            for k, nk in enumerate(G.nodes()):
                if G.node[nk]["type"] == 1:
                    if sim_matrix[j, k] > maxn:
                        maxn = sim_matrix[j, k]
                        max_name = nk
            if maxn > 1e-6:
                res[nj] = (max_name, maxn)
    test(res, init_res, i + 1)

