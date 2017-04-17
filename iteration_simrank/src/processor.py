#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: sunmeng(sunmeng94@163.com)
"""
import cPickle
import math
import numpy as np
import sys

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
                candidates = [(u"急性心肌梗死", 0.0)]
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
        nonzero_row_index, nonzero_col_index = np.nonzero(self.matrix)
        total = len(nonzero_row_index)
        for i in range(total):
            x = nonzero_row_index[i]
            y = nonzero_col_index[i]
            #print self.id2name[x], self.id2name[y], self.matrix[x][y]

    def edge(self, name1, name2):
        #print name1, name2, self.matrix[self.name2id[name1], self.name2id[name2]]
        return self.matrix[self.name2id[name1], self.name2id[name2]]

    def popSim(self, name):
        return self.pop_sim[self.name2id[name]]


class Processor:
    def __init__(self):
        self.network = None
    
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

    def personalized_page_rank(self, s, matrix):
        e = np.zeros((matrix.shape[0], 1), dtype = float)
        e[s] = 1
        w = e
        for k in range(PPR_ITERATION_TIMES):
            w = (1 - PPR_JUMP_PROB) * np.dot(matrix, w) + PPR_JUMP_PROB * e
        return w

    def disambiguate(self, record, preprocessed_record=None):
        if preprocessed_record is None:
            preprocessed_record = process_record(record)
        if self.network is None:
            return preprocessed_record

        vertex_mapping = {
            "main": [],
            "other": []
        }
        vertex_max = {
            "main": [],
            "other": []
        }
        vertexes = []
        for key in preprocessed_record:
            for i, name_group in enumerate(preprocessed_record[key]):
                vertex_ids = []
                vertex_max[key].append(len(vertexes))
                sum_iSim = 0.0
                for name, value in name_group:
                    vertex = {
                        "home": (key, i),
                        "name": name,
                        "iSim": POPSIM_FACTOR *self.network.popSim(name) + value
                    }
                    #print self.network.popSim(name), value
                    vertex_ids.append(len(vertexes))
                    vertexes.append(vertex)
                    sum_iSim += vertex["iSim"]
                if sum_iSim > 0:
                    for k in vertex_ids:
                        vertexes[k]["iSim"] /= sum_iSim
                vertex_mapping[key].append(vertex_ids)
        for i, vertex in enumerate(vertexes):
            #print i, vertex["name"]
            #print vertex["home"], vertex["name"], vertex["iSim"]
            pass
        n = len(vertexes)
        matrix = np.zeros([n, n])
        for i, v1 in enumerate(vertexes):
            for j, v2 in enumerate(vertexes):
                if i != j:
                    matrix[i, j] = self.network.edge(v1["name"], v2["name"])
        row_sum = np.sum(matrix, axis=1)
        for i in range(n):
            if row_sum[i] > 0:
                for j in range(n):
                    matrix[i, j] /= row_sum[i]
        matrix = np.transpose(matrix)
        ppr_matrix = np.zeros([n, 0])
        for i, vertex in enumerate(vertexes):
            w = self.personalized_page_rank(i, matrix)
            ppr_matrix = np.column_stack((ppr_matrix, w))
        for k in range(100):
            coh = [0] * n
            ppr_sum = 0
            for e in range(n):
                if k == 0:
                    s_array = range(n)
                else:
                    s_array = []
                    for key in vertex_max:
                        s_array += vertex_max[key]
                for s in s_array:
                    if vertexes[s]["home"] != vertexes[e]["home"]:
                        coh[e] += ppr_matrix[s, e] * vertexes[e]["iSim"]
                        ppr_sum += ppr_matrix[s, e]
                        #print k, e, s, ppr_matrix[s, e], coh[e]
            ppr_avg = ppr_sum / n
            score = [0] * n
            for e in range(n):
                score[e] = coh[e] + ppr_avg * vertexes[e]["iSim"]
                #print e, coh[e], ppr_avg * vertexes[e]["iSim"], score[e]
            changed = False
            for key in vertex_max:
                for i, vertex_list in enumerate(vertex_mapping[key]):
                    #print vertex_list
                    max_id, max_score = -1, -1
                    for e in vertex_list:
                        if max_id == -1 or score[e] > max_score:
                            max_id, max_score = e, score[e]
                    if max_id != vertex_max[key][i]:
                        changed = True
                        vertex_max[key][i] = max_id
            if not changed:
                break
            #print vertex_max
        #print vertex_max
        #print record
        #print preprocessed_record
        res_record = {
            "main": [[] for i in range(len(preprocessed_record["main"]))],
            "other": [[] for i in range(len(preprocessed_record["other"]))],
        }
        for i, vertex in enumerate(vertexes):
            key, order = vertex["home"]
            #print order
            res_record[key][order].append((vertex["name"], score[i]))
        #print res_record
        for key in res_record:
            for i, res_list in enumerate(res_record[key]):
                res_record[key][i] = sorted(res_list, key=lambda x: x[1], reverse=True)
        #print res_record
        return res_record


processor = Processor()
processor.load_network()
