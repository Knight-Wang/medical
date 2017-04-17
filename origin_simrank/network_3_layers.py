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
    values = d.query('select ICD, 疾病名称 from i2025')

    normal_diseases = {}  # 标准疾病名称字典 <key, value> = <名称, 编码>
    for v in values:
        normal_diseases[v[1]] = v[0]

    print '标准疾病名称个数为 %d' % len(normal_diseases)

    values = d.query('select ICD, 疾病名称 from heart_names_4')

    normal_diseases_4 = {}  # 标准疾病名称亚目字典 <key, value> = <4位编码, 名称>
    for v in values:
        normal_diseases_4[v[0]] = v[1]

    print '标准疾病亚目名称个数为 %d' % len(normal_diseases_4)

    values = d.query('select ICD, 手术名称 from heart_surgery')
    normal_surgeries = {}  # 标准手术名称字典 <key, value> = <名称, 编码>
    for v in values:
        normal_surgeries[v[1]] = v[0]

    print '标准手术名称个数为 %d' % len(normal_surgeries)

    medical_records = d.query('select  S050100, S050200, S050600, S050700, \
                                       S050800, S050900, S051000, S051100, \
                                       S056000, S056100, S056200, \
                                       S050501, S051201, S051301, S051401, \
                                       S051501, S057001, S057101, S057201, \
                                       S057301, S057401 \
                                  from heart_new limit 50000')

    print '医疗记录为 %d 条' % len(medical_records)

    return normal_diseases, normal_diseases_4, normal_surgeries, medical_records


def write_G(G, not_single):
    """ 将伴病网络的写入文件
    :param G: 伴病网络字典，使用 networkx 实现
    :param not_single: 出现过不止一次的点集合
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

    nodes_list = list(G.nodes_iter(data='Label'))
    f = open("visual_new/out/graph_nodes.csv", "w")
    try:
        f.writelines('Id,Label,Type,\n')
        for x in nodes_list:
            if x[0] not in not_single:  # 过滤掉没有邻居的节点
                continue
            tmp = ''
            tmp += x[0]
            tmp += ','
            tmp += x[1]['Label']
            tmp += ','
            tmp += x[1]['Type']
            tmp += ',\n'
            f.writelines(tmp)
    finally:
        f.close()


def get_graph(normal_diseases, normal_diseases_4, normal_surgeries, medical_records):
    """ 构建伴病网络
    :param normal_diseases: 标准疾病名称集合
    :param normal_surgeries: 标准手术名称集合
    :param medical_records: 医疗记录
    :return: G -> 构建好的伴病网络，使用 networkx 实现
             not_single -> 至少有一个邻居的 疾病 或 手术 名称（非孤立点）集合
    """

    total_disease = set()  # 已经识别出来的标准疾病名称集合
    total_surgeries = set()  # 已经识别出来的标准手术名称集合
    union_times = {}  # tuple(a, b) 出现的次数
    single_times = {}  # 疾病或手术名称出现的次数
    G = nx.DiGraph()  # 伴病网络

    for t in medical_records:
        one_main_dis = ''  # 主诊断
        vice_dis = set()  # 副诊断集合
        surgeries = set()  # 手术集合
        now = 0
        for s in t:
            now += 1
            if not s:
                continue
            if now <= 11:  # 这个是疾病名称
                if s in normal_diseases.keys():
                    name_4 = normal_diseases_4[normal_diseases[s][:5]]  # 找到这个6位名称所对应的4位名称
                    if now == 1:
                        dis_ID = name_4 + "_main"  # 相同的疾病名称在不同的记录中可能分别作为主诊断和副诊断，
                                                   # 这里在后面加上后缀 "_main" 或 "_vice" 来区分
                        if dis_ID not in G.nodes():
                            G.add_node(dis_ID, Type='main_dis', Label=normal_diseases[s][:5])
                        one_main_dis = dis_ID
                    else:
                        dis_ID = name_4 + "_vice"
                        if dis_ID not in G.nodes():
                            G.add_node(dis_ID, Type='vice_dis', Label=normal_diseases[s][:5])
                        vice_dis.add(dis_ID)
                    total_disease.add(name_4)
                    if dis_ID not in single_times:
                        single_times[dis_ID] = 1
                    single_times[dis_ID] += 1
            else:  # 这个是手术名称
                if s in normal_surgeries.keys():
                    sur_ID = s + "_sur"
                    G.add_node(sur_ID, Type='sur', Label=normal_surgeries[s])
                    surgeries.add(sur_ID)
                    total_surgeries.add(s)
                    if sur_ID not in single_times:
                        single_times[sur_ID] = 1
                    single_times[sur_ID] += 1

        if not one_main_dis:
            continue

        for v in vice_dis:  # 添加主诊断和副诊断之间的边
            tmp = (min(one_main_dis, v), max(one_main_dis, v))
            if tmp in union_times:
                union_times[tmp] += 1
            else:
                union_times[tmp] = 1

        for s in surgeries:  # 添加主诊断和手术之间的边
            tmp = (min(one_main_dis, s), max(one_main_dis, s))
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


normal_diseases, normal_diseases_4, normal_surgeries, medical_records = init()
G, not_single = get_graph(normal_diseases, normal_diseases_4, normal_surgeries, medical_records)
write_G(G, not_single)  # 把图写入文件
