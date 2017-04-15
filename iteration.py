#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import DataBase
import networkx as nx
import SimRank
from Preprocess import process, getMappingResult, addBrotherNodes, getNormalNames, getICDTree
reload(sys)
sys.setdefaultencoding('utf8')


def dic2list(dic):
    """ 将字典dic按照value（相似度）排序（降序）后放入列表中返回
    :param dic: 字典 <key, value> = <标准疾病名称, 相似度>
    :return: [(标准疾病名称1, 相似度1), [(标准疾病名称2, 相似度2), ...](降序)
    """
    l = [(k, v) for (k, v) in dic.iteritems()]
    l = sorted(l, cmp=lambda x, y: cmp(x[1], y[1]), reverse=True)
    return l


def get_cand_init():
    d = DataBase.DataBase()
    values = d.query('select ICD, 疾病名称 from I2025')
    normal = getNormalNames(values)  # (normalized_name, ICD-10)
    icd4_dic = getICDTree(normal)
    return normal, icd4_dic


def get_cand(unnormalized_name, normal, icd4_dic):
    p_name = process(unnormalized_name)
    name_dict, match_type = getMappingResult(p_name, normal)
    # 不加父节点
    if match_type == 4:
        name_dict = addBrotherNodes(p_name, name_dict, icd4_dic, normal)
    return name_dict


def init():
    """ 初始化
    :return: 标准疾病名称字典,
             标准手术名称字典,
             医疗记录,
             标注数据
    """
    d = DataBase.DataBase()
    values = d.query('select ICD, 疾病名称 from I2025')

    normal_diseases = {}  # 标准疾病名称字典 <key, value> = <名称, 编码>
    for v in values:
        normal_diseases[v[1]] = v[0]

    print '标准疾病名称个数为 %d' % len(normal_diseases)

    values = d.query('select ICD, 手术名称 from heart_surgery')
    normal_surgeries = {}  # 标准手术名称字典 <key, value> = <名称, 编码>
    for v in values:
        normal_surgeries[v[1]] = v[0]

    print '标准手术名称个数为 %d' % len(normal_surgeries)

    medical_records_2013 = d.query('select  S050100, S050200, S050600, S050700, \
                                            S050800, S050900, S051000, S051100, \
                                            S056000, S056100, S056200, \
                                            S050501, S051201, S051301, S051401, \
                                            S051501, S057001, S057101, S057201, \
                                            S057301, S057401 \
                                       from heart_new_2013')

    medical_records_2014_15 = d.query('select  S050100, S050200, S050600, S050700, \
                                               S050800, S050900, S051000, S051100, \
                                               S056000, S056100, S056200, \
                                               S050501, S051201, S051301, S051401, \
                                               S051501, S057001, S057101, S057201, \
                                               S057301, S057401 \
                                          from heart_new')

    medical_records_2013[len(medical_records_2013):len(medical_records_2013)] = medical_records_2014_15

    print '医疗记录为 %d 条' % len(medical_records_2013)

    values = d.query('select 非标准名称, 标准疾病名 from LabeledData_3')
    labeled_data = {}
    for s in values:
        labeled_data[s[0].strip()] = s[1].strip()

    print '测试数据个数为 %d' % len(labeled_data)

    return normal_diseases, normal_surgeries, medical_records_2013, labeled_data


def write_G(G, file_name):
    f = open(file_name, "w")
    n = len(G)
    f.writelines(str(n) + "\n")
    for x in G.nodes():
        if len(G.out_edges(x)):
            f.writelines(x + " " + str(len(G.out_edges(x))) + "\n")
            edges = list(G.out_edges_iter(x, data='weight'))
            for y in edges:
                f.writelines(y[1] + " " + str(y[2]) + "\n")
    f.close()


def write_bad_names(bad_names, file_name):
    f = open(file_name, "w")
    n = len(bad_names)
    f.writelines(str(n) + "\n")
    for x in bad_names:
        if len(bad_names[x]):
            f.writelines(x + " | " + str(len(bad_names[x])) + "\n")
            for y in bad_names[x]:
                f.writelines(y + "\n")
    f.close()


def get_graph(normal_diseases, normal_surgeries, medical_records, labeled_data):
    """ 构建伴病网络
    :param normal_diseases: 标准疾病名称集合
    :param normal_surgeries: 标准手术名称集合
    :param medical_records: 医疗记录
    :return: G -> 构建好的伴病网络，使用 networkx 实现
             not_single -> 至少有一个邻居的 疾病 或 手术 名称（非孤立点）集合
    """

    # 预处理所需的初始化操作
    normal, icd4_dic = get_cand_init()

    total_disease = set()  # 已经识别出来的标准疾病名称集合
    total_surgeries = set()  # 已经识别出来的标准手术名称集合
    union_times = {}  # tuple(a, b) 出现的次数
    single_times = {}  # 疾病或手术名称出现的次数
    G = nx.DiGraph()  # 伴病网络
    bad_names = {}  # 存储labeled_data中的非标准疾病名称的标准名称邻居们
    cnt = 0  # 记录数量
    # cache = {}

    for t in medical_records:
        cnt += 1
        if not (cnt % 100000):
            print cnt
        main_dis = ''  # 主诊断
        vice_dis = set()  # 副诊断集合
        surgeries = set()  # 手术集合
        now = 0  # 列数
        bad = set()  # 这条记录中的存在于labeled_data中的非标准名称集合
        normal_names = set()  # 这条记录中的标准名称集合
        for s in t:
            s = s.strip()
            now += 1
            if not s:
                continue
            if s == 'NA':
                continue
            if now <= 11:  # 这个是疾病名称
                if s in normal_diseases.keys():
                    if now == 1:  # 主诊断
                        main_dis = s
                    else:  # 副诊断
                        vice_dis.add(s)
                    normal_names.add(s)
                    total_disease.add(s)
                    if s not in single_times:
                        single_times[s] = 1
                    single_times[s] += 1
                else:  # 这是个非标准的疾病名称
                    if s in labeled_data.keys():
                        bad.add(s)
                    # tmp = ''
                    # if s in cache.keys():  # 加快速度
                    #     tmp = cache[s]
                    # else:
                    #     name_dic = get_cand(s, normal, icd4_dic)  # 获得候选名称字典
                    #     if name_dic:
                    #         name_list = dic2list(name_dic)
                    #         tmp = name_list[0][0]
                    #         cache[s] = tmp
                    # if tmp:
                    #     total_disease.add(tmp)
                    #     if now == 1:
                    #         main_dis = tmp
                    #     else:
                    #         vice_dis.add(tmp)
                    #     if tmp not in single_times:
                    #         single_times[tmp] = 1
                    #     single_times[tmp] += 1
            else:  # 这个是手术名称
                if s in normal_surgeries.keys():
                    surgeries.add(s)
                    normal_names.add(s)
                    total_surgeries.add(s)
                    if s not in single_times:
                        single_times[s] = 1
                    single_times[s] += 1

        for b in bad:  # 记录非标准副诊断名称和它的标准疾病名称邻居
            if not normal_names:  # 没有标准名称邻居就不添加
                continue
            if b not in bad_names.keys():
                bad_names[b] = set()
            for n in normal_names:
                bad_names[b].add(n)

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

    for k, v in union_times.iteritems():
        v1 = v * 1.0 / single_times[k[0]]  # 权值1
        G.add_edge(k[0], k[1], weight=v1)
        v2 = v * 1.0 / single_times[k[1]]  # 权值2
        G.add_edge(k[1], k[0], weight=v2)

    return G, bad_names


def disambiguate(labeled_data, sim_res, bad_names):
    normal, icd4_dic = get_cand_init()
    for u_name, n_name in labeled_data:
        name_dic = get_cand(u_name, normal, icd4_dic)
        name_list = dic2list(name_dic)
        name_list[0][0]


normal_dis, normal_sur, records, labeled_data = init()
G, bad_names = get_graph(normal_dis, normal_sur, records, labeled_data)

write_G(G, "iteration_texts/out/graph.txt")
write_bad_names(bad_names, "iteration_texts/out/bad_names.txt")

s = SimRank.SimRank(graph_file="iteration_texts/out/graph.txt")
s.sim_rank()
res = s.get_result()
s.print_result("iteration_texts/out/similarity.txt")

ret = disambiguate(labeled_data, res, bad_names)




