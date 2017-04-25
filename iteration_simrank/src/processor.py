#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: sunmeng(sunmeng94@163.com)
"""
import cPickle
import math
import numpy as np
import sys
import copy
import random

import candidate_generator
from conf import *


def process_record(record):
    pred_record = {
        "main": [],
        "other": []
    }
    for key in record:
        for name in record[key]:
            candidates = candidate_generator.generate_candidate(name)
            if len(candidates) == 0:
                candidates = [(u"急性ST段抬高型心肌梗塞", 0.0)]
            pred_record[key].append(candidates)
    return pred_record


class Network:
    def __init__(self, records):
        self.name2id = {}
        self.id2name = []
        for i, line in enumerate(open(DICT_FILE, "r")):
            name = line.rstrip("\n").decode("UTF-8").split("\t")[1]
            self.id2name.append(name)
            self.name2id[name] = i
        self.n = len(self.id2name)
        self.matrix = np.ones([self.n, self.n])
        self.pop_sim = [1] * self.n

        for record in records:
            id_list = []
            for candidates in record["main"] + record["other"]:
                try:
                    name = candidates[0][0]
                except:
                    continue
                id_list.append(self.name2id[name])
            for i, x in enumerate(id_list):
                self.pop_sim[x] += 1
                for j, y in enumerate(id_list):
                    if i != j:
                        self.matrix[x, y] += 1
        #self.pop_sim = map(lambda x: math.log(x), self.pop_sim)
        pop_sum = float(sum(self.pop_sim))
        self.pop_sim = map(lambda x: x / pop_sum, self.pop_sim)
        for i in range(self.n):
            for j in range(self.n):
                self.matrix[i, j] = math.log(self.matrix[i, j] + 1)
        # nonzero_row_index, nonzero_col_index = np.nonzero(self.matrix)
        # total = len(nonzero_row_index)
        # for i in range(total):
        #    x = nonzero_row_index[i]
        #    y = nonzero_col_index[i]
        #    print self.id2name[x], self.id2name[y], self.matrix[x][y]

    def edge(self, name1, name2):
        #print name1, name2, self.matrix[self.name2id[name1], self.name2id[name2]]
        return self.matrix[self.name2id[name1], self.name2id[name2]]

    def popSim(self, name):
        return self.pop_sim[self.name2id[name]]


class Processor:
    def __init__(self):
        self.network = None
        self.sim_matrix = None
    
    def set_network(self, network):
        self.network = network

    def save_network(self):
        try:
            print >> sys.stderr, "Saving network..."
            with open(NETWORK_FILE, "wb") as data_file:
                cPickle.dump(self.network, data_file, True)
        except:
            print >> sys.stderr, "Can not Save,"

    def load_network(self):
        try:
            print >> sys.stderr, "Loading network..."
            with open(NETWORK_FILE, "rb") as data_file:
                self.network = cPickle.load(data_file)
        except:
            print >> sys.stderr, "Network file is not available"

    def simrank(self):
        """ simrank 算法，计算任意两个标准疾病名称之间的相似度
        :return: 相似度矩阵
        """
        trans_matrix = copy.deepcopy(self.network.matrix)  # 转移概率矩阵
        col_sum = np.sum(trans_matrix, axis=0)
        n = len(col_sum)
        for j in range(n):
            if col_sum[j] > 0:
                for i in range(n):
                    trans_matrix[i, j] /= col_sum[j]
        # print trans_matrix
        self.sim_matrix = np.identity(n) * (1.0 - SIMRANK_DAMP)

        for i in range(SIMRANK_ITERATION_TIMES):
            self.sim_matrix = SIMRANK_DAMP * np.dot(np.dot(trans_matrix.transpose(), self.sim_matrix), trans_matrix) \
                              + (1.0 - SIMRANK_DAMP) * np.identity(n)

    def cal_sim(self, neigh_list):
        """ 计算某个候选名称与邻居集合的相似度
        :param neigh_list: 非标准疾病名称的邻居列表
        :return: 相似度
        """
        if not len(neigh_list):
            return 0.0
        total_sim = 0.0
        for i in range(self.network.n):
            for j in range(len(neigh_list)):
                id = self.network.name2id[neigh_list[j]]
                if i != id:
                    total_sim += self.sim_matrix[i, id]
        total_sim /= self.network.n
        total_sim /= len(neigh_list)
        return total_sim

    def disambiguate_simrank(self, record, preprocessed_record=None):
        """ 使用 simrank 进行消歧
        :param record: 原始记录
        :param preprocessed_record: 处理过的记录
        :return: 重新处理过的记录
        """
        if preprocessed_record is None:
            preprocessed_record = process_record(record)
        if self.network is None:
            return preprocessed_record

        all_names = {"main": [], "other": []}  # 先把这条记录中的所有名称对应的标准名称统一放到一个字典里面
        for key in record:
            for candidate_list in preprocessed_record[key]:
                all_names[key].append(candidate_list[0][0])

        res_record = {"main": [], "other": []}  # 返回结果

        for key in record:
            for i, u_name in enumerate(record[key]):
                neigh = []  # 找到非标准疾病名称的邻居
                for key1 in all_names:
                    if key1 != key:
                        for n_name in all_names[key1]:
                            neigh.append(n_name)
                    else:
                        for j, n_name in enumerate(all_names[key1]):
                            if i == j:
                                continue
                            neigh.append(n_name)

                candidate_list = preprocessed_record[key][i]  # 得到非标准疾病名称的候选列表
                res_list = []  # 结果列表
                sim_sum = 0.0  # 归一化
                tmp_sim = []
                for j, c in enumerate(candidate_list):
                    sim = self.cal_sim(neigh)
                    tmp_sim.append(sim)
                    sim_sum += sim
                if sim_sum > 1e-6:
                    for j in range(len(tmp_sim)):
                        tmp_sim[j] /= sim_sum
                    for j, c in enumerate(candidate_list):  # c[0]候选标准疾病名称，c[1]相似度
                        # print tmp_sim[j], c[1]
                        sim = SIMRANK_FACTOR * tmp_sim[j] + (1 - SIMRANK_FACTOR) * c[1]
                        # print sim
                        res_list.append((c[0], sim))
                    res_list = sorted(res_list, key=lambda x: x[1], reverse=True)
                else:
                    res_list = candidate_list
                res_record[key].append(res_list)

        return res_record


processor = Processor()
processor.load_network()

