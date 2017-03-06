#!/usr/bin/env python
# coding=utf-8

import numpy as np
import mysql.connector
import DataBase as db
import codecs

class SimRank(object):

    def __init__(self, c=0.8, it=100, graph_file=''):
        self.nodes = []                   # 所有的节点存入数组
        self.nodes_index = {}             # <节点名，节点编号>
        self.damp = c                     # 阻尼系数
        self.trans_matrix = np.matrix(0)  # 转移概率矩阵
        self.sim_matrix = np.matrix(0)    # 节点相似度矩阵
        self.iter = it                    # 最大迭代次数
        self.link_in = {}                 # 点的入点集合字典
        self.link_out = {}                # 点的出点集合字典
        if graph_file != '':
            self.init_param(graph_file)

    def init_param(self, graph_file):  # 从文件中读取图结构
        f = codecs.open(graph_file, "r", "utf-8")
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
        # 初始化转移概率矩阵
        self.trans_matrix = np.zeros((len(self.nodes), len(self.nodes)))
        for node, in_neighbors in self.link_in.items():
            num = len(in_neighbors)
            prob = 1.0 / num
            for neighbor in in_neighbors:
                self.trans_matrix[neighbor, node] = prob
        # 初始化相似度矩阵
        self.sim_matrix = np.identity((len(self.nodes))) * (1 - self.damp)

    # 一次迭代
    def iterate(self):
        self.sim_matrix = self.damp * np.dot(np.dot(self.trans_matrix.transpose(), self.sim_matrix),
                                             self.trans_matrix) + (1 - self.damp) * np.identity(len(self.nodes))

    # sim_rank算法
    def sim_rank(self):
        # print "nodes:"
        # print self.nodes_index
        # print "trans ratio:"
        # print self.trans_matrix
        for i in range(self.iter):
            print "iteration %d" % (i + 1)
            self.iterate()
            # print self.sim_matrix

    # 得到结果
    def get_result(self):
        res = {}
        for i in range(len(self.nodes)):
            neighbour = []
            for j in range(len(self.nodes)):
                if i != j:
                    sim = self.sim_matrix[i, j].round(4)
                    if not sim:
                        sim = 0
                    if sim > 0:
                        neighbour.append((self.nodes[j], sim))
            # 按相似度由大到小排序
            neighbour = sorted(
                neighbour, cmp=lambda x, y: cmp(x[1], y[1]), reverse=True)
            res[self.nodes[i]] = [x for x in neighbour]
        return res

    # 打印结果
    def print_result(self, sim_node_file):
        # 打印node之间的相似度
        f_out_user = open(sim_node_file, "w")
        for i in range(len(self.nodes)):
            f_out_user.write(self.nodes[i] + "\t")
            neighbour = []
            for j in range(len(self.nodes)):
                if i != j:
                    sim = self.sim_matrix[i, j].round(4)
                    if not sim:
                        sim = 0
                    if sim > 0:
                        neighbour.append((j, sim))
            # 按相似度由大到小排序
            neighbour = sorted(
                neighbour, cmp=lambda x, y: cmp(x[1], y[1]), reverse=True)
            for (u, sim) in neighbour:
                f_out_user.write(self.nodes[u] + ":" + str(sim) + "\t")
            f_out_user.write("\n")
        f_out_user.close()

    # 计算某个候选标准疾病名称（gn）和某个待消歧的非标准疾病名称的
    # 好邻居们（good）的相似度均值
    def cal(self, gn, good):
        i = self.nodes_index[gn]
        ave = 0.0
        for g in good:
            j = self.nodes_index[g]
            ave += self.sim_matrix[i, j]
        if len(good):
            return ave / len(good)
        return 0.0

    @staticmethod
    def get_normal():
        d = db.DataBase()
        values = d.query('select 疾病名称 from norm6')
        normal = set()  # 标准疾病名称集合
        for t in values:
            for s in t:
                normal.add(s)
        return normal

    # 将非标准疾病名称分类
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
