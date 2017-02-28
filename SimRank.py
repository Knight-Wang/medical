#!/usr/bin/env python
# coding=utf-8

import numpy as np
import mysql.connector


class SimRank(object):

    def __init__(self, c=0.8, it=100):
        self.nodes = []                   # 所有的节点存入数组
        self.nodes_index = {}             # <节点名，节点编号>
        self.damp = c                     # 阻尼系数
        self.trans_matrix = np.matrix(0)  # 转移概率矩阵
        self.sim_matrix = np.matrix(0)    # 节点相似度矩阵
        self.iter = it                    # 最大迭代次数
        self.link_in = {}                 # 点的入点集合字典
        self.link_out = {}                # 点的出点集合字典

    def init_param(self, graph_file):
        f = open(graph_file, "r")
        while True:
            line = f.readline()
            if not line:
                break
            arr = line.split()
            node = arr[0]
            if node in self.nodes_index:
                node_id = self.nodes_index[node]
            else:
                node_id = len(self.nodes)
                self.nodes_index[node] = node_id
                self.nodes.append(node)
            for ele in arr[1:]:
                out_neighbor = ele
                if out_neighbor in self.nodes_index:
                    out_neighbor_id = self.nodes_index[out_neighbor]
                else:
                    out_neighbor_id = len(self.nodes)
                    self.nodes_index[out_neighbor] = out_neighbor_id
                    self.nodes.append(out_neighbor)
                in_neighbors = []
                if out_neighbor_id in self.link_in:
                    in_neighbors = self.link_in[out_neighbor_id]
                in_neighbors.append(node_id)
                self.link_in[out_neighbor_id] = in_neighbors

        self.trans_matrix = np.zeros((len(self.nodes), len(self.nodes)))
        for node, in_neighbors in self.link_in.items():
            num = len(in_neighbors)
            prob = 1.0 / num
            for neighbor in in_neighbors:
                self.trans_matrix[neighbor, node] = prob

        self.sim_matrix = np.identity((len(self.nodes))) * (1 - self.damp)

    def iterate(self):
        self.sim_matrix = self.damp * np.dot(np.dot(self.trans_matrix.transpose(), self.sim_matrix),
                                             self.trans_matrix) + (1 - self.damp) * np.identity(len(self.nodes))

    def sim_rank(self, graph_file):
        self.init_param(graph_file)
        print "nodes:"
        print self.nodes_index
        print "trans ratio:"
        print self.trans_matrix
        for i in range(self.iter):
            print "iteration %d:" % (i + 1)
            self.iterate()
            print self.sim_matrix

    def cal(self, gn, good):
        i = self.nodes_index[gn]
        sum = 0.0
        for g in good:
            j = self.nodes_index[g]
            sum += self.sim_matrix[i, j]
        if len(good):
            return sum / len(good)
        return 0.0

    @staticmethod
    def get_normal():
        conn = mysql.connector.connect(user='root',
                                       password='123456',
                                       database='medical',
                                       use_unicode='True')
        cursor = conn.cursor(buffered=True)

        cursor.execute('select 疾病名称 from norm6')

        values = cursor.fetchall()
        normal = set()  # 标准疾病名称集合

        for t in values:
            for s in t:
                normal.add(s)
        return normal

    def classify(self):
        f = open("bad_names.txt", "r")
        f1 = open("result.txt", "w")
        try:
            while True:
                con = f.readline()
                if not con:
                    break
                tmp = con.split()
                x = tmp[0]
                max_n = 0.0
                best = ''
                good = set()  # 这个坏节点的好邻居们
                for y in tmp[1:]:
                    good.add(y)
                for gn in self.nodes:
                    res = self.cal(gn, good)
                    if res > max_n:
                        max_n = res
                        best = gn
                f1.writelines(x + ' ' + best + ' ' + str(max_n) + '\n')
        finally:
            f.close()
            f1.close()
    pass
