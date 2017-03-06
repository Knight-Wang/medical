#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import datetime
import re
import codecs
import SimRank as sr
import DataBase as db
import Preprocess
from Preprocess import *

reload(sys)
sys.setdefaultencoding('utf8')


def process(name):
    result = name.replace('&nbsp;', '')
    result = re.split('\(|\)| |\*|（|）|\[|\]|【|】|,|，|、|;|；', result)
    return [x for x in filter(lambda x: x != '', result)]


def is_normal(l, n):
    for x in l:
        if x in n:
            return x
    return None


def transform(x):
    if isinstance(x, unicode):
        return x.decode('utf-8')
    return x


def same(x, y):
    return (x == y) or \
           (x == '不稳定性心绞痛' and y == '增强型心绞痛') or \
           (x == '增强型心绞痛' and y == '不稳定性心绞痛')


def cal(norm1, norm2, sim_rank):
    ok1 = transform(norm1)
    ok2 = transform(norm2)
    if ok1 not in sim_rank.keys():
        return 0.0
    for tup in range(len(sim_rank[ok1])):
        if sim_rank[ok1][tup][0] == ok2:
            return sim_rank[ok1][tup][1]
    return 0.0


def classify(bad_one, candidate, good_neigh, sim_mat):
    res = {}
    max_sim = -1.0
    best_one = '$$$'
    can_list = [(k, v) for (k, v) in candidate.iteritems()]
    can_list = sorted(can_list, cmp=lambda x, y: cmp(x[1], y[1]), reverse=True)
    if bad_one not in good_neigh.keys():
        return can_list, None, can_list[0][0], None
    for c, sim in can_list:
        sum_s = 0.0
        for gn in good_neigh[bad_one]:
            sum_s += cal(c, gn, sim_mat)
        if not len(good_neigh[bad_one]):
            res[c] = 0.0
        else:
            sum_s /= len(good_neigh[bad_one])  # 候选标名和坏名字的好邻居们的平均相似度
            res[c] = sum_s
        if sum_s > max_sim:
            max_sim = sum_s
            best_one = c
    return can_list, good_neigh[bad_one], best_one, res

if __name__ == "__main__":

    d = db.DataBase()
    values = d.query('select ICD, 疾病名称 from i2025')
    normal = getNormalNames(values)
    start_time = datetime.datetime.now()
    # records = d.query('select 出院诊断名称, 出院诊断名称1, 出院诊断名称2, \
    #                           出院诊断名称3, 出院诊断名称4, 出院诊断名称5, \
    #                           出院诊断名称6, 出院诊断名称7, 出院诊断名称8, \
    #                           出院诊断名称9, 出院诊断名称10 \
    #                      from heart')

    records = d.query('select S050100, S050200, S050600, S050700, \
                              S050800, S050900, S051000, S051100, \
                              S056000, S056100, S056200 \
                      from heart_new')
    G = {}
    # total = set()  # 标准疾病名称集合
    # total_bad = {}  # <非标准疾病名称, 出现次数>
    # cnt = 0
    # cnt_all = 0
    bad_names = {}  # 存储非标准疾病名称和它的标准疾病名称邻居们
    for t in records:
        link = set()  # 这条记录中的标准名称集合
        bad = set()  # 这条记录中的非标准名称集合
        for s in t:
            if s:
                # tmp = process(s)
                # res = is_normal(tmp, normal)
                # cnt_all += 1
                if s in normal:  # 成功匹配
                    link.add(s)
                #     total.add(s)
                #     cnt += 1
                else:  # 未匹配
                    bad.add(s)
    #                 if s not in total_bad:
    #                     total_bad[s] = 1
    #                 total_bad[s] += 1
        for b in bad:  # 给“坏”名字添加“好”邻居
            if b not in bad_names:
                bad_names[b] = set()
            for l in link:
                bad_names[b].add(l)
        for x in link:
            for y in link:
                if x not in G:
                    G[x] = set()
                if y not in G:
                    G[y] = set()
                if x != y:
                    G[x].add(y)
                    G[y].add(x)
    # end_time = datetime.datetime.now()
    # print '正确分类的记录个数为 %d' % cnt
    # print '非标准疾病名称个数为 %d' % cnt_all
    # print '运行时间%d秒' % (end_time - start_time).seconds
    # print '已经识别的种类数为 %d' % len(total)
    f = codecs.open("texts/out/graph.txt", "w", "utf-8")
    try:
        for x in G:
            tmp = x
            if len(G[x]):
                tmp += ' '
                l = len(G[x])
                i = 0
                for y in G[x]:
                    tmp += y
                    if i != l - 1:
                        tmp += ' '
                    i += 1
            f.writelines(tmp + '\n')
    finally:
        f.close()

    start_time = datetime.datetime.now()
    s = sr.SimRank(graph_file="texts/out/graph.txt")
    s.sim_rank()
    res = s.get_result()

    # s.print_result("texts/out/similarity.txt")
    end_time = datetime.datetime.now()
    print '节点数: %d' % len(s.nodes)
    print 'sim_rank运行时间为%d' % (end_time - start_time).seconds
    values = d.query('select 非标准名称, 标准疾病名 from labeleddata')
    cnt = 0
    f = open("texts/out/sim_rank_result.txt", "w")
    start_time = datetime.datetime.now()

    cnt_c_y = 0
    cnt_c_n = 0
    cnt_n_y = 0
    cnt_n_n = 0
    checked = False

    for row in values:
        unnormalized_name = row[0].strip()
        normalized_name = row[1].strip()
        p_name = process(unnormalized_name)
        name_dict = getMappingResult(p_name, normal)
        if len(name_dict) != 0:
            if normalized_name in name_dict.keys():  # map correctly
                score = {}
                can_list, good_nei, res_name, score = classify(unnormalized_name, name_dict, bad_names, res)
                f.writelines(str(unnormalized_name) + ':\n')
                f.writelines("好邻居：\n")
                if good_nei:
                   for gn in good_nei:
                       f.writelines(str(gn) + '\n')
                f.writelines('候选 ' + str(len(name_dict.keys())) + ':\n')
                if not can_list:
                    for c in name_dict.keys():
                        f.writelines(str(c) + '\n')
                else:
                    for (c, v) in can_list:
                        f.writelines(str(c) + ' : ' + str(v) + '\n')
                    f.writelines('---------------------------------------\n')
                if score:
                    rank_score = [(c, v) for (c, v) in score.iteritems()]
                    rank_score = sorted(rank_score, cmp=lambda x, y: cmp(x[1], y[1]), reverse=True)
                    if rank_score[0][1] > 1e-5:
                        f.writelines('checked\n')
                        checked = True
                    for x in range(len(rank_score)):
                        f.writelines(str(rank_score[x][0]) + ' : ')
                        f.writelines(str(rank_score[x][1]) + '\n')
                f.writelines('最终选择了: \n')
                f.writelines(str(res_name) + '\n')
                f.writelines('答案是：')
                f.writelines(str(normalized_name) + '\n')
                f.writelines('===========================================\n')
                if same(res_name, normalized_name):
                    f.writelines('yes\n')
                    if checked:
                        cnt_c_y += 1
                    else:
                        cnt_n_y += 1
                    cnt += 1
                else:
                    if checked:
                        cnt_c_n += 1
                    else:
                        cnt_n_n += 1
                    f.writelines('no\n')
            else:  # map to a disease name but the name is not the labeled one.
                pass  # 待处理
        else:  # cannot map
            pass  # 待处理
    end_time = datetime.datetime.now()
    print '经过sim_rank后分类正确的个数为 %d' % cnt
    print '分类运行时间为 %d' % (end_time - start_time).seconds

    f.writelines(str(cnt_c_y) + '\n')
    f.writelines(str(cnt_c_n) + '\n')
    f.writelines(str(cnt_n_y) + '\n')
    f.writelines(str(cnt_n_n) + '\n')
    f.close()
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
