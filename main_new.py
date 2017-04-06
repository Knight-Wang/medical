#!/usr/bin/env python
# -*- coding: utf-8 -*-

import networkx as nx
import sys
import DataBase
import copy
from Preprocess import process, getMappingResult, getNormalNames, addBrotherNodes, getICDTree

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
    values = d.query('select ICD, 疾病名称 from i2025')

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

    return normal_diseases, normal_surgeries, medical_records_2013


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


def get_graph(normal_diseases, normal_surgeries, medical_records):
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
    bad_names = {}  # 存储非标准疾病主诊断名称和它的标准疾病名称邻居们
    bad_names_vice = {}  # 存储非标准疾病副诊断名称和它的标准疾病名称邻居们

    for t in medical_records:
        one_main_dis = ''  # 主诊断
        vice_dis = set()  # 副诊断集合
        surgeries = set()  # 手术集合
        is_normal = True  # 这条记录中的主诊断是否是标准疾病名称
        bad_vice = set()  # 这条记录中的非标准副诊断疾病名称
        now = 0
        for s in t:
            s = s.strip()
            s = ' '.join(s.split())
            now += 1
            if not s:
                continue
            if s == 'NA':
                continue
            if now <= 11:  # 这个是疾病名称
                if s in normal_diseases.keys():
                    if now == 1:  # 主诊断
                        dis_ID = s + "_main"  # 相同的疾病名称在不同的记录中可能分别作为主诊断和副诊断，
                                                   # 这里在后面加上后缀 "_main" 或 "_vice" 来区分
                        if dis_ID not in G.nodes():
                            G.add_node(dis_ID, Type='main_dis', Label=normal_diseases[s])
                        one_main_dis = dis_ID
                    else:
                        dis_ID = s + "_vice"
                        if dis_ID not in G.nodes():
                            G.add_node(dis_ID, Type='vice_dis', Label=normal_diseases[s])
                        vice_dis.add(dis_ID)
                    total_disease.add(s)
                    if dis_ID not in single_times:
                        single_times[dis_ID] = 1
                    single_times[dis_ID] += 1
                else:  # 这是个非标准的疾病名称
                    if now == 1:  # 非标准疾病名称中的主诊断
                        is_normal = False
                        one_main_dis = s
                    else:  # 非标准疾病名称中的副诊断
                        bad_vice.add(s)
            else:  # 这个是手术名称
                if s in normal_surgeries.keys():
                    sur_ID = s + "_surg"
                    G.add_node(sur_ID, Type='sur', Label=normal_surgeries[s])
                    surgeries.add(sur_ID)
                    total_surgeries.add(s)
                    if sur_ID not in single_times:
                        single_times[sur_ID] = 1
                    single_times[sur_ID] += 1

        for b in bad_vice:  # 记录非标准副诊断名称和它的标准疾病名称邻居
            if (one_main_dis and is_normal) or vice_dis or surgeries:  # 没有标准疾病名称邻居就不添加
                if b not in bad_names_vice:
                    bad_names_vice[b] = set()
                if one_main_dis and is_normal:
                    bad_names_vice[b].add(one_main_dis)
                for v in vice_dis:
                    bad_names_vice[b].add(v)
                for s in surgeries:
                    bad_names_vice[b].add(s)

        if not one_main_dis:
            continue

        if is_normal:  # 主诊断是标准疾病名称

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

        else:  # 主诊断是非标准疾病名称
            if vice_dis or surgeries:  # 这条记录中的副诊断集合和手术集合如果都为空的话是没有意义的
                                       # 至少一个不为空才把它们作为邻居信息记录下来
                if one_main_dis not in bad_names.keys():
                    bad_names[one_main_dis] = set()
                for v in vice_dis:
                    bad_names[one_main_dis].add(v)
                for s in surgeries:
                    bad_names[one_main_dis].add(s)

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

    return G, not_single, bad_names, bad_names_vice


def filter_interested_names(G, interested_names):
    """
    :param G: 伴病网络
    :param interested_names: 感兴趣的疾病名称集合
    :return: neighbors: 感兴趣的疾病名称入边字典，<key, value> = <疾病名称, set(出边集合)>
    """
    neighbors = {}  # 出点字典
    for i in interested_names:
        name = i + "_main"
        neighbors[name] = copy.copy(G.neighbors(name))

    f = open("main_new_texts/out/neighbors.txt", "w")
    f.writelines(str(len(neighbors)) + "\n")
    try:
        for i in interested_names:
            name = i + "_main"
            f.writelines(name + " | " + str(len(neighbors[name])) + "\n")
            for x in neighbors[name]:
                f.writelines(x + "\n")
            f.writelines("\n")
    finally:
        f.close()
    return neighbors


def write_bad_names(bad_names, file_name):
    f = open(file_name, "w")
    try:
        f.writelines(str(len(bad_names)) + "\n")
        for x in bad_names.keys():
            f.writelines(x + " | " + str(len(bad_names[x])) + "\n")
            for y in bad_names[x]:
                f.writelines(y + "\n")
            f.writelines("\n")
    finally:
        f.close()


def read_file(file_name):
    res = {}
    f = open(file_name, "r")
    num = int(f.readline().strip())
    while num:
        line = f.readline().strip()
        line = line.split('|')
        name = line[0].strip()
        res[name] = set()
        n = int(line[1].strip())
        while n:
            res[name].add(f.readline().strip())
            n -= 1
        f.readline()
        num -= 1
    return res


def read_data():
    neighbors = read_file("main_new_texts/out/neighbors.txt")
    bad_names = read_file("main_new_texts/out/bad_names_dic.txt")
    bad_names_vice = read_file("main_new_texts/out/bad_names_vice_dic.txt")
    return neighbors, bad_names, bad_names_vice


def write_neigh(u_name, bad_names, bad_names_vice, f):
    f.writelines(u_name + "\n")
    if u_name in bad_names.keys():
        f.writelines("作为主诊断出现时邻居有 | " + str(len(bad_names[u_name])) + '\n')
        for x in bad_names[u_name]:
            f.writelines(x + '\n')
        f.writelines('\n')
    if u_name in bad_names_vice.keys():
        f.writelines("作为副诊断出现时邻居有 | " + str(len(bad_names_vice[u_name])) + '\n')
        for x in bad_names_vice[u_name]:
            f.writelines(x + '\n')
        f.writelines('\n')


# 获得消歧所需要的数据，并持久化保存在文件中
# normal_diseases, normal_surgeries, medical_records = init()
# G, not_single, bad_names, bad_names_vice = get_graph(normal_diseases, normal_surgeries, medical_records)
# write_bad_names(bad_names, "main_new_texts/out/bad_names_dic.txt")
# write_bad_names(bad_names_vice, "main_new_texts/out/bad_names_vice_dic.txt")
# interested_names = load_interested_names()
# neighbors = filter_interested_names(G, interested_names)


d = DataBase.DataBase()
values = d.query('select ICD, 疾病名称 from I2025')
normal = getNormalNames(values)  # (normalized_name, ICD-10)
icd4_dic = getICDTree(normal)

neighbors, bad_names, bad_names_vice = read_data()

values = d.query('select ICD, 非标准名称, 标准疾病名 from LabeledData')

print '测试集总记录数为 %d' % (len(values))

preprocess_ok = open("main_new_texts/out/res/preprocess_ok.txt", "w")
not_in_dic = open("main_new_texts/out/res/not_in_dic.txt", "w")
need_fur_pro_low = open("main_new_texts/out/res/need_fur_pro_low.txt", "w")
need_fur_pro_high = open("main_new_texts/out/res/need_fur_pro_high.txt", "w")
cnt = 0
cnt_ok = 0
cnt_not_in_dic = 0
cnt_need_fur_pro = 0
cnt_neigh_low = 0
cnt_neigh_high = 0

for row in values:
    unnormalized_name = row[1].strip()
    normalized_name = row[2].strip()
    p_name = process(unnormalized_name)
    name_dict, match_type = getMappingResult(p_name, normal)
    # 不加父节点
    if match_type == 4:
        name_dict = addBrotherNodes(p_name, name_dict, icd4_dic, normal)
    # name_dict is the candidate set(name : sim)
    len_candidates = len(name_dict)
    sort_name_list = sorted(name_dict.items(), key=lambda d: d[1], reverse=True)
    if len_candidates != 0:
        str_pair = [k + ":" + str(v) for (k, v) in sort_name_list]
        if normalized_name in name_dict.keys():  # map correctly
            cnt += 1
            if sort_name_list[0][1] >= 0.85:
                cnt_ok += 1
                preprocess_ok.writelines(unnormalized_name + " | " + sort_name_list[0][0] + " | " + normalized_name + "\n")
            else:
                normalized_name = normalized_name.encode("utf-8")
                unnormalized_name = unnormalized_name.encode("utf-8")
                # 在这里进行消歧
                if (unnormalized_name not in bad_names.keys()) and (unnormalized_name not in bad_names_vice.keys()):
                    cnt_not_in_dic += 1
                    not_in_dic.writelines(unnormalized_name + "\n")
                else:
                    cnt_need_fur_pro += 1

                    cnt_neigh = 0  # 记录邻居个数，将邻居个数太少的分开

                    if unnormalized_name in bad_names.keys():
                        cnt_neigh += len(bad_names[unnormalized_name])
                    if unnormalized_name in bad_names_vice.keys():
                        cnt_neigh += len(bad_names_vice[unnormalized_name])

                    if cnt_neigh > 3:
                        cnt_neigh_high += 1
                        write_neigh(unnormalized_name, bad_names, bad_names_vice, need_fur_pro_high)
                    else:
                        cnt_neigh_low += 1
                        write_neigh(unnormalized_name, bad_names, bad_names_vice, need_fur_pro_low)

        else:  # map to a disease name but the name is not the labeled one.
            pass
    else:  # cannot map
        pass

print '有效记录数为 %d 条' % cnt
print '相似度很高，无需消歧的记录有 %d 条' % cnt_ok
print '不在非标准名称字典中，无法消歧的有 %d 条' % cnt_not_in_dic
print '可以进行消歧的有 %d 条' % cnt_need_fur_pro
print '邻居数量过少的记录有 %d 条' % cnt_neigh_low
print '邻居数量较多的记录有 %d 条' % cnt_neigh_high

preprocess_ok.close()
not_in_dic.close()
need_fur_pro_low.close()
need_fur_pro_high.close()