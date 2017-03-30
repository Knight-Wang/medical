#!/usr/bin/env python
# -*- coding: utf-8 -*-

import networkx as nx
import sys
import DataBase
reload(sys)
sys.setdefaultencoding('utf8')


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


def write_nodes(G, not_single):
    """ 将伴病网络的节点写入文件
    :param G: 伴病网络字典，使用networkx实现
    :return: 无
    """

    nodes = list(G.nodes_iter(data='Type'))
    f = open("visual_new/out/graph_nodes.csv", "w")
    try:
        f.writelines('Id,Type,\n')
        for x in nodes:
            if x[0] not in not_single:
                continue
            tmp = ''
            tmp += x[0]
            tmp += ','
            tmp += x[1]['Type']
            tmp += ',\n'
            f.writelines(tmp)
    finally:
        f.close()


def write_edges(G):
    """ 将伴病网络的边集合写入文件
    :param G: 伴病网络字典，使用networkx实现
    :return: 无
    """

    edges = list(G.edges_iter(data='weight', default=1))
    f = open("visual_new/out/graph_edges.csv", "w")
    try:
        f.writelines('Source,Target,Weight,\n')
        for x in edges:
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
        main_dis = ''  # 主诊断
        vice_dis = set()  # 副诊断集合
        surgeries = set()  # 手术集合
        now = 0
        for s in t:
            now += 1
            if not s:
                continue
            if now <= 11:
                if s in normal_diseases:
                    if now == 1:
                        G.add_node(s, Type='main_dis')
                        main_dis = s
                    else:
                        G.add_node(s, Type='vice_dis')
                        vice_dis.add(s)
                    total_disease.add(s)
                    if s not in single_times:
                        single_times[s] = 1
                    single_times[s] += 1
            else:
                if s in normal_surgeries:
                    G.add_node(s, Type='sur')
                    surgeries.add(s)
                    total_surgeries.add(s)
                    if s not in single_times:
                        single_times[s] = 1
                    single_times[s] += 1

        if not main_dis:
            continue

        for v in vice_dis:  # 添加主诊断和副诊断之间的边
            tmp = (min(main_dis, v), max(main_dis, v))
            if tmp in union_times:
                union_times[tmp] += 1
            else:
                union_times[tmp] = 1

        for s in surgeries:  # 添加主诊断和手术之间的边
            tmp = (min(main_dis, s), max(main_dis, s))
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
write_nodes(G, not_single)  # 把节点写入文件
write_edges(G)  # 把边写入文件
