#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import datetime
import re
import codecs
import SimRank as sr
import DataBase as db
from Preprocess import *
import copy

reload(sys)
sys.setdefaultencoding('utf8')


def is_normal(l, n):
    for x in l:
        if x in n:
            return x
    return None


def transform(x):
    if isinstance(x, unicode):
        return x.decode('utf-8')
    return x


def cal(norm1, norm2, sim_rank):
    ok1 = transform(norm1)
    ok2 = transform(norm2)
    if ok1 not in sim_rank.keys():
        return 0.0
    for tup in range(len(sim_rank[ok1])):
        if sim_rank[ok1][tup][0] == ok2:
            return sim_rank[ok1][tup][1]
    return 0.0


def dic2list(dic):
    l = [(k, v) for (k, v) in dic.iteritems()]
    l = sorted(l, cmp=lambda x, y: cmp(x[1], y[1]), reverse=True)
    return l


def classify(bad_one, candidate, good_neigh, sim_mat):
    res = {}
    can_list = dic2list(candidate)
    if abs(can_list[0][1] - 1.0) <= 1e-5 or \
       (bad_one not in good_neigh.keys()) or \
       not len(good_neigh[bad_one]):
        return candidate, False
    for c, sim in can_list:
        sum_s = 0.0
        for gn in good_neigh[bad_one]:
            sum_s += cal(c, gn, sim_mat)
        sum_s /= len(good_neigh[bad_one])  # 候选标名和坏名字的好邻居们的平均相似度
        res[c] = sum_s
    return res, True


def weighting(before, after, multiple ,ratio):  # simrank之前结果字典，simrank之后结果字典，之后所占加权系数
    res = copy.copy(before)
    for k in res.iterkeys():
        res[k] = res[k] * (1.0 - ratio) + after[k] * multiple * ratio
    return res


def alias(name):
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
    # if top_k == 1:
    #     if len(l) > 1 and l[1][1] == l[0][1]:
    #         return label == l[1][0] or label == l[0][0]
    #     return label == l[0][0]
    r = min(top_k, len(l))
    tmp_l = [l[i][0] for i in range(r)]
    tmp = alias(label)
    for t in tmp:
        if t in tmp_l:
            return True
    return False


def print_right_log(right_file, bad_name, before, after, label, cnt):  # 把之前分错而simrank分对的记录打印到正确日志中
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


def print_wrong_log(wrong_file, bad_name, before, after, label, cnt):  # 把之前分对而simrank分错的记录打印到错误日志中
    wrong_file.writelines(str(cnt) + '\n')
    wrong_file.writelines('非标准疾病名称：\n')
    wrong_file.writelines(bad_name + '\n')
    wrong_file.writelines("simrank之前：\n")
    for x in range(len(before)):
        wrong_file.writelines(before[x][0] + " : " + str(before[x][1]) + '\n')
    wrong_file.writelines("---------------------------------------------------\n")
    wrong_file.writelines("simrank之后：\n")
    for x in range(len(after)):
        wrong_file.writelines(after[x][0] + " : " + str(after[x][1]) + '\n')
    wrong_file.writelines("---------------------------------------------------\n")
    wrong_file.writelines("正确答案:\n")
    wrong_file.writelines(label + '\n')
    wrong_file.writelines("=================================================\n")


if __name__ == "__main__":

    d = db.DataBase()
    values = d.query('select ICD, 疾病名称 from I2025')
    normal = getNormalNames(values)
    icd4_dic = getICDTree(normal)

    values = d.query('select 类目编码,类目名称 from Norm3')
    icd3_dict = {}
    for row in values:
        icd3_dict[row[0]] = row[1]
    start_time = datetime.datetime.now()

    values = d.query('select 手术名称 from heart_surgery')
    normal_surgery = set()  # 标准手术名称集合
    for t in values:
        for s in t:
            normal_surgery.add(s)

    records = d.query('select S050100, S050200, S050600, S050700, \
                              S050800, S050900, S051000, S051100, \
                              S056000, S056100, S056200, \
                              S050501, S051201, S051301, S051401, \
                              S051501, S057001, S057101, S057201, \
                              S057301, S057401 \
                         from heart_new')

    G = {}
    bad_names = {}  # 存储非标准疾病名称和它的标准疾病名称邻居们
    appear = {}
    co_appear = {}
    for t in records:
        link = set()  # 这条记录中的标准名称集合
        bad = set()  # 这条记录中的非标准名称集合
        now = 0
        for s in t:
            now += 1
            if s:
                if now < 11:
                    if s in normal:  # 成功匹配
                        link.add(s)
                        if s not in appear:
                            appear[s] = 1
                        appear[s] += 1
                    else:  # 未匹配
                        bad.add(s)
                else:
                    if s in normal_surgery:
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
            if len(G[x]):
                f.writelines(tmp + ' ' + str(len(G[x])) + '\n')
                for y in G[x]:
                    f.writelines(y)
                    a = min(x, y)
                    b = max(x, y)
                    val = co_appear[(a, b)]
                    f.writelines(' ' + str(val) + '\n')
    finally:
        f.close()

    start_time = datetime.datetime.now()
    s = sr.SimRank(graph_file="texts/out/graph.txt")
    s.sim_rank()
    res = s.get_result()

    s.print_result("texts/out/similarity.txt")

    end_time = datetime.datetime.now()
    print '节点数: %d' % len(s.nodes)
    print 'sim_rank运行时间为%d' % (end_time - start_time).seconds
    values = d.query('select 非标准名称, 标准疾病名 from labeleddata')
    cnt_before = 0
    cnt_after = 0
    cnt_weighted = 0
    cnt_noise = 0
    cnt_correct = 0
    f = open("texts/out/sim_rank_result.txt", "w")
    wrong = open("texts/out/sim_rank_wrong.txt", "w")
    right = open("texts/out/sim_rank_right.txt", "w")
    start_time = datetime.datetime.now()
    TopK = 1
    for row in values:
        unnormalized_name = row[0].strip()
        normalized_name = row[1].strip()
        p_name = process(unnormalized_name)

        name_dict, match_type = getMappingResult(p_name, normal)
        if match_type != 4:  # 精确匹配和半精确匹配
            name_dict = addFatherNode(p_name, name_dict, icd3_dict, normal)
        else:
            name_dict = addFatherAndBrotherNodes(p_name, name_dict, icd3_dict, icd4_dic, normal)

        if len(name_dict) != 0:
            if normalized_name in name_dict.keys():  # map correctly
                re_rank, checked = classify(unnormalized_name, name_dict, bad_names, res)
                if checked:
                    weighted = weighting(name_dict, re_rank, 1, 0.5)
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
                            print_wrong_log(wrong, unnormalized_name, rank, re_rank, normalized_name, cnt_noise)
                    f.writelines('++++++++++++++++++++++++++++++++++++++++++++\n')
                    f.writelines('加权之后结果：\n')
                    f.writelines(weighted[0][0] + '\n')
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
    # f = codecs.open("bad_names.txt", "w", "utf-8")
    # try:
    #     for b in bad_names:
    #         tmp = b
    #         cnt = len(bad_names[b])
    #         if cnt:
    #             tmp += ' '
    #             i = 0
    #             for gn in bad_names[b]:
    #                 tmp += gn
    #                 if i != cnt - 1:
    #                     tmp += ' '
    #                 i += 1
    #         f.writelines(tmp + '\n')
    # finally:
    #     f.close()

    # f = open("bad_guys.txt", "w")
    # res = sorted(total_bad.iteritems(), key=lambda d: d[1], reverse=True)
    # try:
    #     for x in res:
    #         tmp = ''
    #         tmp += x[0]
    #         tmp += ' '
    #         tmp += str(x[1])
    #         f.writelines(tmp + '\n')
    # finally:
    #     f.close()
