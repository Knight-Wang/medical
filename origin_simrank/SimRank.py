#!/usr/bin/env python
# coding=utf-8

import numpy as np
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
        nodes = int(f.readline())
        while nodes:
            nodes -= 1
            line = f.readline()
            arr = line.split()
            node = arr[0]
            if node in self.nodes_index:
                node_id = self.nodes_index[node]
            else:
                node_id = len(self.nodes)
                self.nodes_index[node] = node_id
                self.nodes.append(node)
            edges = int(arr[1].decode('utf-8'))
            while edges:
                edges -= 1
                out = f.readline().split()
                out_neighbor = out[0]
                degree = float(out[1].decode('utf-8'))
                if out_neighbor in self.nodes_index:
                    out_neighbor_id = self.nodes_index[out_neighbor]
                else:
                    out_neighbor_id = len(self.nodes)
                    self.nodes_index[out_neighbor] = out_neighbor_id
                    self.nodes.append(out_neighbor)
                in_neighbors = []
                if out_neighbor_id in self.link_in:
                    in_neighbors = self.link_in[out_neighbor_id]
                in_neighbors.append((node_id, degree))
                self.link_in[out_neighbor_id] = in_neighbors

        # 初始化转移概率矩阵
        self.trans_matrix = np.zeros((len(self.nodes), len(self.nodes)))
        for node, in_neighbors in self.link_in.items():
            num = 0
            for i in range(len(in_neighbors)):
                num += in_neighbors[i][1]
            for neighbor in in_neighbors:
                prob = neighbor[1] * 1.0 / num
                self.trans_matrix[neighbor[0], node] = prob
        # print self.trans_matrix
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
            if not (i % 20):
                print "iteration %d" % (i + 1)
            self.iterate()

    # 得到结果
    def get_result(self):
        res = {}
        for i in range(len(self.nodes)):
            neighbour = []
            for j in range(len(self.nodes)):
                if i != j:
                    sim = self.sim_matrix[i, j].round(6)
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
                    sim = self.sim_matrix[i, j].round(6)
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
