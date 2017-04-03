#!/usr/bin/env python
# -*- coding: utf-8 -*-

import networkx as nx
import sys
import DataBase
reload(sys)
sys.setdefaultencoding('utf8')


def load_interested_names():
    """ 从文件中读入关注的标准疾病名称
    :return: set -> 关注的标准疾病名称集合
    """
    interested_names = set()
    f = open("neighbour_test_texts/in/interest.txt", "r")
    try:
        while True:
            line = f.readline().strip()
            if not line:
                break
            interested_names.add(line.decode('utf-8'))
    finally:
        f.close()
    return interested_names


def init():
    """ 初始化
    :return: 标准疾病名称字典,
             标准手术名称字典,
             医疗记录
    """
    d = DataBase.DataBase()
    values = d.query('select 疾病名称 from i2025')
    normal_diseases = set()  # 标准疾病名称集合
    for t in values:
        for s in t:
            normal_diseases.add(s)

    print '标准疾病名称个数为 %d' % len(normal_diseases)

    values = d.query('select 手术名称 from heart_surgery')
    normal_surgeries = set()  # 标准手术名称集合
    for t in values:
        for s in t:
            normal_surgeries.add(s)

    print '标准手术名称个数为 %d' % len(normal_surgeries)

    medical_records = d.query('select  S050100, S050200, S050600, S050700, \
                                       S050800, S050900, S051000, S051100, \
                                       S056000, S056100, S056200, \
                                       S050501, S051201, S051301, S051401, \
                                       S051501, S057001, S057101, S057201, \
                                       S057301, S057401 \
                                  from heart_new')

    print '医疗记录为 %d 条' % len(medical_records)

    return normal_diseases, normal_surgeries, medical_records


def write_nodes(G, not_single, interested_names):
    """ 将伴病网络的节点写入文件
    :param G: 伴病网络字典，使用networkx实现
    :return: 无
    """

    nodes = list(G.nodes_iter(data='Type'))
    f = open("neighbour_test_texts/out/graph_nodes.csv", "w")
    try:
        f.writelines('Id,Type,\n')
        for x in nodes:
            if x[0] not in not_single:
                continue
            if x[0] not in interested_names:
                continue
            tmp = ''
            tmp += x[0]
            tmp += ','
            tmp += x[1]['Type']
            tmp += ',\n'
            f.writelines(tmp)
    finally:
        f.close()


def write_edges(G, interested_names):
    """ 将伴病网络的边集合写入文件
    :param G: 伴病网络字典，使用networkx实现
    :return: 无
    """

    edges = list(G.edges_iter(data='weight', default=1))
    f = open("neighbour_test_texts/out/graph_edges.csv", "w")
    try:
        f.writelines('Source,Target,Weight,\n')
        for x in edges:
            if (x[0] not in interested_names) and (x[1] not in interested_names):
                continue
            tmp = ''
            tmp += x[0]
            tmp += ','
            tmp += x[1]
            tmp += ','
            tmp += str(x[2])
            tmp += ',\n'
            f.writelines(tmp)
    finally:
        f.close()


def get_graph(normal_diseases, normal_surgeries, medical_records):
    """ 构建伴病网络
    :param normal_diseases: 标准疾病名称集合
    :param normal_surgeries: 标准手术名称集合
    :param medical_records: 医疗记录
    :return:
    """

    total_disease = set()  # 已经识别出来的标准疾病名称集合
    total_surgeries = set()  # 已经识别出来的标准手术名称集合
    union_times = {}
    single_times = {}
    G = nx.DiGraph()
    for t in medical_records:
        link = set()
        now = 0
        for s in t:
            now += 1
            if not s:
                continue
            if now <= 11:
                if s in normal_diseases:
                    G.add_node(s, Type='dis')
                    link.add(s)
                    total_disease.add(s)
                    if s not in single_times:
                        single_times[s] = 1
                    single_times[s] += 1
            else:
                if s in normal_surgeries:
                    G.add_node(s, Type='sur')
                    link.add(s)
                    total_surgeries.add(s)
                    if s not in single_times:
                        single_times[s] = 1
                    single_times[s] += 1
        for x in link:
            for y in link:
                if x < y:
                    tmp = (x, y)
                    if tmp in union_times:
                        union_times[tmp] += 1
                    else:
                        union_times[tmp] = 1

    print '已经识别的疾病种类数为 %d' % len(total_disease)
    print '已经识别的手术种类数为 %d' % len(total_surgeries)

    not_single = set()
    for k, v in union_times.iteritems():
        v1 = v * 1.0 / single_times[k[0]]  # 权值1
        G.add_edge(k[0], k[1], weight=v1)
        v2 = v * 1.0 / single_times[k[1]]  # 权值2
        G.add_edge(k[1], k[0], weight=v2)
        not_single.add(k[0])
        not_single.add(k[1])

    return G, not_single


normal_diseases, normal_surgeries, medical_records = init()
G, not_single = get_graph(normal_diseases, normal_surgeries, medical_records)
interested_names = load_interested_names()
write_nodes(G, not_single, interested_names)  # 把至少有一个邻居并且感兴趣的节点写入文件
write_edges(G, interested_names)  # 把包含感兴趣的节点的边写入文件
