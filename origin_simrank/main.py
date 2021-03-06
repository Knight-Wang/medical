#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import SimRank as sr
import DataBase as db
from Preprocess import *
import copy
import math
from util import getNormalNames, getICDTree

reload(sys)
sys.setdefaultencoding('utf8')


def transform(x):
    """ uft-8 解码
    :param x: 解码前
    :return: 解码后
    """
    if isinstance(x, unicode):
        return x.decode('utf-8')
    return x


def cal(norm1, norm2, sim_rank, net):
    """ 计算两个标准疾病名称间的相似度
    :param norm1: 标准疾病名称1
    :param norm2: 标准疾病名称2
    :param sim_rank: simrank相似度矩阵
    :return: norm1 和 norm2 的 simrank 相似度, 伴病网络中没有相应的标准疾病名称返回 None
    """
    ok1 = transform(norm1)
    ok2 = transform(norm2)
    if ok1 == ok2:
        return 1.0
    if ok1 not in sim_rank.keys():
        return None
    res = 0.0
    flag = False
    flag2 = True
    for tup in range(len(sim_rank[ok1])):
        if sim_rank[ok1][tup][0] == ok2:
            res = sim_rank[ok1][tup][1]
            flag = True
    # for tup in range(len(net[ok1])):
    #     if net[ok1][tup][0] == ok2:
    #         res *= net[ok1][tup][1]
    #         flag2 = True
    if res > 0.0 and flag and flag2:
        return res
    return None


def cal_plus(G, can_name, neigh, sim_rank, net):
    """ 计算某个非标准疾病名称 m 的一个候选标准疾病名称 can_name 的邻居集合
        与 m 的伴病标准疾病名称邻居集合 neigh 的平均相似度
    :param G: 伴病网络
    :param can_name: m 的一个候选标准疾病名称
    :param neigh: m 的伴病标准疾病名称邻居集合
    :param sim_rank: simrank 相似度矩阵
    :param net: 边权调整
    :return: 平均相似度
    """
    ok1 = transform(can_name)
    if ok1 not in G.keys():
        return None, None
    if not len(G[ok1]):
        return None, None

    sum = 0.0
    cnt = 0
    neigh_sim = {}
    for x in G[ok1]:
        neigh_avg = 0.0
        cnt_avg = 0
        for n in neigh:
            tmp = cal(x, n, sim_rank, net)
            if tmp:
                neigh_avg += tmp
                cnt_avg += 1
                sum += tmp
                cnt += 1
        if cnt_avg:
            neigh_avg /= cnt_avg
            neigh_sim[x] = neigh_avg
    if cnt:
        return sum / cnt, neigh_sim
    return None, None


def dic2list(dic):
    """ 将字典dic按照value（相似度）排序（降序）后放入列表中返回
    :param dic: 字典 <key, value> = <标准疾病名称, 相似度>
    :return: [(标准疾病名称1, 相似度1), [(标准疾病名称2, 相似度2), ...](降序)
    """
    l = [(k, v) for (k, v) in dic.iteritems()]
    l = sorted(l, cmp=lambda x, y: cmp(x[1], y[1]), reverse=True)
    return l


def classify(G, bad_one, candidate, good_neigh, sim_mat, net):
    """ 将非标准疾病名称 bad_one 分类
    :param bad_one: 非标准疾病名称
    :param candidate: 候选名称字典 <key, value> = <标准疾病名称, 相似度>
    :param good_neigh: 所有非标准疾病名称的伴病字典 <key, value> = <非标准疾病名称, set(标准伴病1, 标准伴病2, ...)>
    :param sim_mat: simrank 相似度矩阵
    :param net: 边权调整
    :return: simrank 计算后的候选名称字典 <key, value> = <标准疾病名称, 相似度>,
             是否经过 simrank 计算(相似度很高不用计算, bad_one 没出现过或没有邻居无法计算),
             具体到每个邻居的相似度字典 <key, value> = <邻居, 相似度>
    """
    res = {}
    neigh_sim_dic = {}
    can_list = dic2list(candidate)
    if abs(can_list[0][1] - 1.0) <= 1e-5 or \
       (bad_one not in good_neigh.keys()) or \
       not len(good_neigh[bad_one]):
        return candidate, False, None
    # if can_list[0][1] > 0.857:  # 减小噪声，如果排名第一的候选相似度很高（大于0.857），就不再进行sim_rank
    #     return candidate, False, None
    flag = True
    for c, sim in can_list:
        tmp, neigh_sim = cal_plus(G, c, good_neigh[bad_one], sim_mat, net)
        if not tmp:
            flag = False
            break
        else:
            res[c] = tmp
            neigh_sim_dic[c] = neigh_sim
    if flag:
        return res, True, neigh_sim_dic
    return candidate, False, None


def weighting(before, after, ratio):
    """ 预处理结果和simrank处理结果加权
    :param before: simrank之前结果字典 <key, value> = <标准疾病名称, 相似度>
    :param after: simrank之后结果字典 <key, value> = <标准疾病名称, 相似度>
    :param ratio: simrank之后所占加权系数 float in [0, 1]
    :return: 加权结果字典 <key, value> = <标准疾病名称, 相似度>
    """
    max_val = max(val for val in after.itervalues())
    if max_val < 1e-5:
        return before
    tmp = {}
    for (k, v) in after.iteritems():
        tmp[k] = v / max_val
    res = copy.copy(before)
    for k in res.iterkeys():
        res[k] = res[k] * (1.0 - ratio) + tmp[k] * ratio
    return res


def alias(name):
    """
    :param name: 标准疾病名称
    :return: 标准疾病名称的所有别名集合, 没有返回本身
    """
    res = set()
    if name == '不稳定性心绞痛' or name == '增强型心绞痛':
        res.add('不稳定性心绞痛')
        res.add('增强型心绞痛')
    elif name == '冠状动脉痉挛' or name == '变异型心绞痛':
        res.add('冠状动脉痉挛')
        res.add('变异型心绞痛')
    else:
        res.add(name)
    return res


def verdict(l, label, top_k):
    """ 验证 top_k 计算结果中是否包含正确结果(label)
    :param l: top_k 结果 list [(标准名称1, 相似度1), (标准名称2, 相似度2), ...](降序)
    :param label: 标注的正确结果
    :param top_k: 选取排名前几
    :return: 是否正确
    """
    r = min(top_k, len(l))
    tmp_l = [l[i][0] for i in range(r)]
    tmp = alias(label)
    for t in tmp:
        if t in tmp_l:
            return True
    return False


def print_right_log(right_file, bad_name, before, after, label, cnt):
    """ 把之前分错而 simrank 分对的记录打印到正确日志中
    :param right_file:
    :param bad_name:
    :param before:
    :param after:
    :param label:
    :param cnt:
    :return:
    """
    right_file.writelines(str(cnt) + '\n')
    right_file.writelines('非标准疾病名称：\n')
    right_file.writelines(bad_name + '\n')
    right_file.writelines("simrank之前：\n")
    for x in range(len(before)):
        right_file.writelines(before[x][0] + " : " + str(before[x][1]) + '\n')
    right_file.writelines("---------------------------------------------------\n")
    right_file.writelines("simrank之后：\n")
    for x in range(len(after)):
        right_file.writelines(after[x][0] + " : " + str(after[x][1]) + '\n')
    right_file.writelines("---------------------------------------------------\n")
    right_file.writelines("正确答案:\n")
    right_file.writelines(label + '\n')
    right_file.writelines("=================================================\n")


def print_wrong_log(wrong_file, bad_name, before, after, label, cnt, graph, neigh_sim_dic):
    """ 把之前分对而simrank分错的记录打印到错误日志中
    :param wrong_file:
    :param bad_name:
    :param before:
    :param after:
    :param label:
    :param cnt:
    :param graph:
    :param neigh_sim_dic:
    :return:
    """
    wrong_file.writelines(str(cnt) + '\n')
    wrong_file.writelines('非标准疾病名称：\n')
    wrong_file.writelines(bad_name + '\n')
    wrong_file.writelines("simrank之前：\n")
    for x in range(len(before)):
        wrong_file.writelines(before[x][0] + " : " + str(before[x][1]) + '\n')
    wrong_file.writelines("---------------------------------------------------\n")
    wrong_file.writelines("simrank之后：\n")
    for x in range(len(after)):
        wrong_file.writelines("候选" + str(x + 1) + " --> ")
        wrong_file.writelines(after[x][0] + " : " + str(after[x][1]) + '\n')
        wrong_file.writelines("++++++++++++++++++++++++++++++++++\n")
        for k, v in neigh_sim_dic[after[x][0]].iteritems():
            wrong_file.writelines(k + str(v) + "\n")
        wrong_file.writelines("++++++++++++++++++++++++++++++++++++\n")
    wrong_file.writelines("---------------------------------------------------\n")
    wrong_file.writelines("正确答案:\n")
    wrong_file.writelines(label + '\n')
    wrong_file.writelines("=================================================\n")


def is_very_similar(bad_name, normal_d, similar_log_file, not_similar_log_file, none_similar_log_file):
    """ 是否非常相似
    :param bad_name:
    :param normal_d:
    :param similar_log_file:
    :param not_similar_log_file:
    :param none_similar_log_file:
    :return:
    """
    bad_name = bad_name.strip()
    p = process(bad_name)
    name_dict, match_type = getMappingResult(p, normal_d)
    if not name_dict:
        none_similar_log_file.writelines(bad_name + "\n")
        return None
    name_list = dic2list(name_dict)
    if name_list[0][1] > 0.857:
        similar_log_file.writelines(bad_name + " : " + name_list[0][0] + " -> " + str(name_list[0][1]) + '\n')
        return name_list[0][0]
    not_similar_log_file.writelines(bad_name + "\n")
    return None


def load_normal_name_dict():
    """ 载入别名字典
    :return: 别名字典 <key, value> = <别名, 标准名称>
    """
    f = open("./Dict/Alias.txt", "r")
    res = {}
    try:
        while True:
            line = f.readline().strip()
            if not line:
                break
            names = line.split(" ")
            normal = names[0].decode("utf-8")
            for e in names:
                res[e.decode("utf-8")] = normal
    finally:
        f.close()
    return res


def build_network(records, disease, surgeries, last_res):
    """ 构建伴病网络
    :param records: 医疗记录
    :param disease: 标准疾病名称集合
    :param surgeries: 标准手术名称集合
    :param last_res: 上次消歧的结果
    :return: 伴病网络字典 <key, value> = <标准疾病名称, set(标准疾病名称1, 标准疾病名称2, ...)>
             非标准疾病名称的伴病(邻居)字典 <key, value> = <非标准疾病名称, set(标准名称1, 标准名称2, ...)>
    """
    G = {}  # 伴病网络 邻接表
    bad_names = {}  # 存储非标准疾病名称和它的标准疾病名称邻居们
    appear = {}  # 单个标准疾病名称出现次数
    co_appear = {}  # <标准疾病名称1, 标准疾病名称2> 出现次数
    alias_dict = load_normal_name_dict()  # 别名字典，把别名都映射成一个确定的标准疾病名称
    cnt_row = 0  # 记录数量
    for t in records:
        cnt_row += 1
        if cnt_row % 100000 == 0:
            print "第 %d 行" % cnt_row
        link = set()  # 这条记录中的标准名称集合
        bad = set()  # 这条记录中的非标准名称集合
        now = 0
        for s in t:
            now += 1
            if not s:
                continue
            if now <= 11:  # 疾病名称
                # segs = process(s)
                # name_dict, type = getMappingResult(segs, disease)
                # if name_dict:
                    # res = dic2list(name_dict)
                    # if res[0][1] > 0.857:  # 可信度比较高，直接认为是标准疾病名称
                if s in disease: #
                    # 在这里解决别名问题
                    n = copy.copy(s)
                    if s in alias_dict:
                        n = alias_dict[s]
                    link.add(n)
                    if n not in appear:
                        appear[n] = 1
                    appear[n] += 1
                elif s in last_res:  # 迭代利用上次消歧的结果
                    s = last_res[s]
                    n = copy.copy(s)
                    if s in alias_dict:
                        n = alias_dict[s]
                    link.add(n)
                    if n not in appear:
                        appear[n] = 1
                    appear[n] += 1
                else:  # 未匹配
                    bad.add(s)
            else:  # 手术名称
                if s in surgeries:
                    link.add(s)
                    if s not in appear:
                        appear[s] = 1
                    appear[s] += 1
        for b in bad:  # 给“坏”名字添加“好”邻居
            if b not in bad_names:
                bad_names[b] = set()
            for l in link:
                bad_names[b].add(l)
        for x in link:
            for y in link:
                if x < y:
                    tmp = (x, y)
                    if tmp not in co_appear:
                        co_appear[tmp] = 1
                    co_appear[tmp] += 1

    for (x, y) in co_appear:
        if x not in G:
            G[x] = set()
        G[x].add(y)
        if y not in G:
            G[y] = set()
        G[y].add(x)

    f = codecs.open("texts/out/graph.txt", "w", "utf-8")
    try:
        f.writelines(str(len(G.keys())) + '\n')
        for x in G:
            tmp = x
            if not len(G[x]):
                continue
            f.writelines(tmp + ' ' + str(len(G[x])) + '\n')
            for y in G[x]:
                f.writelines(y)
                # val = math.log(len(G) * 1.0 / len(G[x]))
                a = min(x, y)
                b = max(x, y)
                val = co_appear[(a, b)] * 1.0 / appear[x]
                f.writelines(' ' + str(val) + '\n')
    finally:
        f.close()

    f = open("texts/out/bad_names.txt", "w")
    try:
        for b in bad_names:
            f.writelines(b + "    ")
            for n in bad_names[b]:
                f.writelines(n + " ")
            f.writelines("\n")
    finally:
        f.close()
    return G, bad_names


def filter_map_well(bad_name, can_dict, map_right_file):
    """ 过滤掉相似度较高的
    :param bad_name:
    :param can_dict:
    :param map_right_file:
    :return:
    """
    tmp_l = dic2list(can_dict)
    flag = False
    if tmp_l[0][1] > 0.857:
        map_right_file.writelines(bad_name + " : " + tmp_l[0][0] + " -> " + str(tmp_l[0][1]) + '\n')
        flag = True
    return flag


def get_can_dict(bad_name, normal, icd4_dic):
    """ 获得候选名称字典，封装了Preprocess.py中的预处理操作
    :param bad_name: 非标准疾病名称, normal
    :param normal: 标准疾病名称字典(6位编码)
    :param icd4_dic: 标准疾病名称(4位编码)
    :return: 候选标准疾病名称字典 <key, value> = <候选名称, 局部相似度>
    """
    p_name = process(bad_name)
    name_dict, match_type = getMappingResult(p_name, normal)

    # 不加父节点
    if match_type == 4:
        name_dict = addBrotherNodes(p_name, name_dict, icd4_dic, normal)

    return name_dict


def init():
    """ 初始化
    :return: normal_disease 标准疾病名称(6位编码)集合,
             icd4_dic 标准疾病名称(4位编码)字典, <key, value> = <icd4, (icd6名称, icd6编码)>
             icd3_dic 标准疾病名称(3位编码)字典,
             normal_surgeries 标准手术名称集合,
             medical_records 医疗记录集合
    """
    d = db.DataBase()
    values = d.query('select ICD, 疾病名称 from I2025')
    normal_disease = getNormalNames(values)
    icd4_dic = getICDTree(normal_disease)

    values = d.query('select 手术名称 from heart_surgery')
    normal_surgeries = set()  # 标准手术名称集合
    for t in values:
        for s in t:
            normal_surgeries.add(s)

    medical_records = d.query('select S050100, S050200, S050600, S050700, \
                                      S050800, S050900, S051000, S051100, \
                                      S056000, S056100, S056200, \
                                      S050501, S051201, S051301, S051401, \
                                      S051501, S057001, S057101, S057201, \
                                      S057301, S057401 \
                                 from heart_new_2013')

    return normal_disease, icd4_dic, normal_surgeries, medical_records


def cal_relatedness(g, x, y):
    """ 计算两个实体的语义相关性
    :param g: 网络字典 <key, value> = <实体名称, [(实体名称1, 相似度1), (实体名称2, 相似度2), ...]>
    :param x: 实体1 string
    :param y: 实体2 string
    :return: 语义相关性 float in [0, 1]
    """
    x_neigh = {}
    y_neigh = {}
    union = set()
    for i in range(len(g[x])):
        x_neigh[g[x][i][0]] = g[x][i][1]
        union.add(g[x][i][0])
    for i in range(len(g[y])):
        y_neigh[g[y][i][0]] = g[y][i][1]
        union.add(g[y][i][0])

    vec1 = []
    vec2 = []
    for ele in union:
        if ele in x_neigh.keys():
            vec1.append(x_neigh[ele])
        else:
            vec1.append(0.0)
        if ele in y_neigh.keys():
            vec2.append(y_neigh[ele])
        else:
            vec2.append(0.0)

    n = len(vec1)
    m1 = 0.0
    m2 = 0.0
    product = 0.0
    for i in range(n):
        product += vec1[i] * vec2[i]
        m1 += vec1[i] * vec1[i]
        m2 += vec2[i] * vec2[i]

    return product * 1.0 / (math.sqrt(m1) * math.sqrt(m2))


def WLM(graph_file):
    """ 使用WLM模型计算两个实体的语义相关性
    :param graph_file: 图文件
    :return: 重新计算之后的网络字典 <key, value> = <实体名称, (实体名称1, 相关度1), (实体名称2, 相关度2) ...>
    """
    g = {}
    f = codecs.open(graph_file, "r", "utf-8")
    fout = open("texts/out/relatedness.txt", "w")
    nodes = int(f.readline())
    fout.writelines(str(nodes) + "\n")
    while nodes:
        nodes -= 1
        line = f.readline()
        arr = line.split()
        node = arr[0]
        g[node] = []
        edges = int(arr[1].decode('utf-8'))
        while edges:
            edges -= 1
            out = f.readline().split()
            out_neighbor = out[0]
            weight = float(out[1].decode('utf-8'))
            g[node].append((out_neighbor, weight))
    f.close()

    res = {}  # 返回值
    for x in g:
        fout.writelines(x + " " + str(len(g[x])) + "\n")
        res[x] = []
        for y in g[x]:
            val = cal_relatedness(g, x, y[0])
            fout.writelines(y[0] + " " + str(val) + "\n")
            res[x].append((y[0], val))

    fout.close()
    return res


def classify_with_WLM(neigh, name_dict, network):
    """ 使用WLM模型分类
    :param bad_name: 非标准疾病名称
    :param neigh: bad_name 的伴病邻居集合
    :param name_dict: 候选实体和相关性字典 <key, value> = <候选实体名称, 相关性值>
    :param network: WLM网络（字典）
    :return: 使用WLM重新计算之后的候选实体和相关性字典 <key, value> = <候选实体名称, 得分>
    """
    for x in name_dict.keys():
        if x not in network.keys():
            return None

    res = {}
    for (c, sim) in name_dict.iteritems():
        sum = 0.0
        for n in neigh:
            for i in range(len(network[c])):
                if network[c][i][0] == n:
                    sum += network[c][i][1]
        sum /= len(network[c])
        res[c] = sum
    return res


if __name__ == "__main__":

    last_res = {}
    for times in range(3):
        print '第 %d 次迭代' % (times + 1)
        normal_disease, icd4_dic, normal_surgeries, medical_records = init()
        start_time = datetime.datetime.now()
        print "开始构建伴病网络"
        G, bad_names = build_network(medical_records, normal_disease, normal_surgeries, last_res)
        end_time = datetime.datetime.now()
        print "构建伴病网络时间为 %d秒" % (end_time - start_time).seconds
        cnt_node = len(G)
        cnt_edge = 0
        for x in G:
            cnt_edge += len(G[x])
        print "节点数：%d" % cnt_node
        print "边数：%d" % cnt_edge

        net = WLM("texts/out/graph.txt")

        start_time = datetime.datetime.now()
        s = sr.SimRank(graph_file="texts/out/graph.txt")
        s.sim_rank()
        res = s.get_result()  # simrank 结果字典

        s.print_result("texts/out/similarity.txt")

        end_time = datetime.datetime.now()
        print '节点数: %d' % len(s.nodes)
        print 'sim_rank运行时间为%d' % (end_time - start_time).seconds
        d = db.DataBase()
        values = d.query('select 非标准名称, 标准疾病名 from labeleddata')
        cnt_before = 0
        cnt_after = 0
        cnt_weighted = 0
        cnt_noise = 0
        cnt_correct = 0
        f = open("texts/out/sim_rank_result.txt", "w")
        wrong = open("texts/out/sim_rank_wrong.txt", "w")
        right = open("texts/out/sim_rank_right.txt", "w")
        map_right_f = open("texts/out/map_right.txt", "w")
        start_time = datetime.datetime.now()
        TopK = 1
        for row in values:
            unnormalized_name = row[0].strip()
            normalized_name = row[1].strip()
            name_dict = get_can_dict(unnormalized_name, normal_disease, icd4_dic)

            if len(name_dict) != 0:
                if normalized_name in name_dict.keys():  # map correctly
                    # ok = filter_map_well(unnormalized_name, name_dict, map_right_f)
                    # if ok:
                    #     continue
                    re_rank, checked, neigh_sim_dic = classify(G, unnormalized_name, name_dict, bad_names, res, net)
                    if checked:
                        weighted = weighting(name_dict, re_rank, 0.4)
                        weighted = dic2list(weighted)
                    re_rank = dic2list(re_rank)
                    f.writelines(str(unnormalized_name) + ':\n')
                    f.writelines('simrank之前 ' + str(len(name_dict.keys())) + ':\n')
                    rank = dic2list(name_dict)
                    for r in range(len(rank)):
                        f.writelines(rank[r][0] + " : " + str(rank[r][1]) + "\n")
                    if checked:
                        f.writelines("simrank之后：\n")
                        for r in range(len(re_rank)):
                            f.writelines(re_rank[r][0] + " : " + str(re_rank[r][1]) + "\n")
                        f.writelines("++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
                        for w in range(len(weighted)):
                            f.writelines(weighted[w][0] + " : " + str(weighted[w][1]) + "\n")
                    f.writelines('答案是：')
                    f.writelines(str(normalized_name) + '\n')
                    f.writelines('simrank之前结果: \n')
                    f.writelines(rank[0][0] + '\n')
                    flag = False
                    if verdict(rank, normalized_name, TopK):
                        f.writelines('yes\n')
                        cnt_before += 1
                        flag = True
                    else:
                        f.writelines('no\n')
                    if checked:
                        f.writelines('------------------------------------------\n')
                        f.writelines('simrank之后结果：\n')
                        f.writelines(re_rank[0][0] + '\n')
                        if verdict(re_rank, normalized_name, TopK):
                            f.writelines('yes\n')
                            cnt_after += 1
                            if not flag:
                                cnt_correct += 1
                                print_right_log(right, unnormalized_name, rank, re_rank, normalized_name, cnt_correct)
                        else:
                            f.writelines('no\n')
                            if flag:
                                cnt_noise += 1
                                print_wrong_log(wrong, unnormalized_name, rank, re_rank, normalized_name, cnt_noise, G, neigh_sim_dic)
                        f.writelines('++++++++++++++++++++++++++++++++++++++++++++\n')
                        f.writelines('加权之后结果：\n')
                        f.writelines(weighted[0][0] + '\n')
                        # last_res[unnormalized_name] = u'是电风扇的'
                        if verdict(weighted, normalized_name, TopK):
                            f.writelines('yes\n')
                            cnt_weighted += 1
                        else:
                            f.writelines("no\n")
                    else:
                        if flag:
                            cnt_after += 1
                            cnt_weighted += 1
                    f.writelines('===========================================\n')

                else:  # map to a disease name but the name is not the labeled one.
                    pass  # 待处理
            else:  # cannot map
                pass  # 待处理
        end_time = datetime.datetime.now()
        print 'sim_rank之前分类正确的个数为 %d' % cnt_before
        print 'sim_rank后分类正确的个数为 %d' % cnt_after
        print '加权之后分类正确的个数为 %d' % cnt_weighted
        print '分类运行时间为 %d' % (end_time - start_time).seconds
        f.close()
        wrong.close()
        right.close()
        map_right_f.close()

