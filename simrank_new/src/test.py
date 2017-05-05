#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cPickle

from conf import *


def verdict(x, y):
    if x == y:
        return True, x
    elif (x == u'不稳定性心绞痛' and y == u'增强型心绞痛') or \
         (x == u'增强型心绞痛' and y == u'不稳定性心绞痛'):
            return True, u'不稳定性心绞痛'
    elif (x == u'冠状动脉痉挛' and y == u'变异型心绞痛') or \
         (x == u'变异型心绞痛' and y == u'冠状动脉痉挛'):
            return True, u'冠状动脉痉挛'
    return False, None


def combine(d):
    tmp = 0
    if u'不稳定性心绞痛' in d:
        tmp += d[u'不稳定性心绞痛']
        d.pop(u'不稳定性心绞痛')
    if u'增强型心绞痛' in d:
        tmp += d[u'增强型心绞痛']
        d.pop(u'增强型心绞痛')

    d[u'不稳定性心绞痛'] = tmp

    tmp = 0
    if u'冠状动脉痉挛' in d:
        tmp += d[u'冠状动脉痉挛']
        d.pop(u'冠状动脉痉挛')
    if u'变异型心绞痛' in d:
        tmp += d[u'变异型心绞痛']
        d.pop(u'变异型心绞痛')

    d[u'冠状动脉痉挛'] = tmp

    return d


def cal_percent(tp, d):
    for x in d:
        if x not in tp:
            d[x] = 0.0
        else:
            d[x] = tp[x] * 1.0 / d[x]
    return d


def f1(precision, recall):
    res = {}
    pre_keys = set(precision.keys())
    re_keys = set(recall.keys())
    tmp_keys = pre_keys | re_keys

    for x in tmp_keys:
        if x not in precision or x not in recall:
            res[x] = 0
        else:
            res[x] = 2 * precision[x] * recall[x] / (precision[x] + recall[x])

    return res


def test_init(name_dict, no_cand):
    precision_num = {}
    recall_num = {}
    for i, record in enumerate(open("../data/test.txt", "r")):
        x = record.rstrip("\n").decode("UTF-8").split("\t")
        for t in x:
            d = t.split("##")
            if d[1] == "NONE":
                continue
            if name_dict[d[0]][0][0] not in precision_num:
                precision_num[name_dict[d[0]][0][0]] = 1
            else:
                precision_num[name_dict[d[0]][0][0]] += 1
            if d[1] not in recall_num:
                recall_num[d[1]] = 1
            else:
                recall_num[d[1]] += 1

    precision_num = combine(precision_num)
    recall_num = combine(recall_num)

    print '精确率字典长度 %d' % len(precision_num)
    print '召回率字典长度 %d' % len(recall_num)

    true_positive = {}  # 真正例字典
    disease_dict = {}
    loop = 0
    for line in open("../data/i2025.txt", "r"):
        loop += 1
        if loop == 1:
            continue
        data = line.rstrip("\n").decode("UTF-8").split("\t")
        disease_dict[data[1]] = data[0]

    WRONG_FILE = "../res/bad_case_init.txt"
    RIGHT_FILE = "../res/good_case_init.txt"
    wrong_file = open(WRONG_FILE, "w")
    right_file = open(RIGHT_FILE, "w")
    cnt_all, correct, wrong, not_in, recall = 0, 0, 0, 0, 0
    num_dist = [0, 0, 0, 0, 0, 0, 0]  # 候选实体数量分布
    for i, record in enumerate(open("../data/test.txt", "r")):
        x = record.rstrip("\n").decode("UTF-8").split("\t")
        for t in x:
            d = t.split("##")
            if d[1] == "NONE":
                continue
            cnt_all += 1
            if d[0] in no_cand:
                not_in += 1
            entity_set = set()
            for e in name_dict[d[0]]:
                entity_set.add(e[0])
            num_dist[len(entity_set) / 2] += 1
            if d[1] in entity_set:
                recall += 1
            res, real_name = verdict(name_dict[d[0]][0][0], d[1])
            if res:
                correct += 1
                if real_name not in true_positive:
                    true_positive[real_name] = 1
                else:
                    true_positive[real_name] += 1

                right_file.writelines(d[0] + " | " + name_dict[d[0]][0][0] + " | " + str(name_dict[d[0]][0][1]) + " | " + d[1] + "\n")
            else:
                wrong += 1
                wrong_file.writelines(d[0] + " | " + name_dict[d[0]][0][0] + " | " + str(name_dict[d[0]][0][1]) + " | " + d[1] + "\n")

    print "not_in %d" % not_in
    print "all %d" % cnt_all
    print "Correct %d" % correct
    print "recall num %d" % recall
    print "recall rate %f" % (recall * 1.0 / cnt_all)
    print '分布：'
    for i, n in enumerate(num_dist):
        print i, n
    print "Wrong %d" % wrong
    print "Percent %.3f" % (correct * 1.0 / (correct + wrong))
    wrong_file.close()
    right_file.close()

    precision_num = cal_percent(true_positive, precision_num)
    recall_num = cal_percent(true_positive, recall_num)
    f1_num = f1(precision_num, recall_num)

    total_sum = sum(precision_num.values())
    total_sum /= len(precision_num)

    print '平均精确率 %.3f' % total_sum

    total_sum = sum(recall_num.values())
    total_sum /= len(recall_num)

    print '平均召回率 %.3f' % total_sum

    total_sum = sum(f1_num.values())
    total_sum /= len(f1_num)

    print '平均f1 %.3f' % total_sum


def test(res, init_res, num):
    precision_num = {}
    recall_num = {}
    for i, record in enumerate(open("../data/test.txt", "r")):
        x = record.rstrip("\n").decode("UTF-8").split("\t")
        for t in x:
            d = t.split("##")
            if d[1] == "NONE":
                continue
            if d[1] not in recall_num:
                recall_num[d[1]] = 1
            else:
                recall_num[d[1]] += 1

            if d[0] not in res:
                if init_res[d[0]] not in precision_num:
                    precision_num[init_res[d[0]]] = 1
                else:
                    precision_num[init_res[d[0]]] += 1
            else:
                if res[d[0]][0] not in precision_num:
                    precision_num[res[d[0]][0]] = 1
                else:
                    precision_num[res[d[0]][0]] += 1

    precision_num = combine(precision_num)
    recall_num = combine(recall_num)

    print '精确率字典长度 %d' % len(precision_num)
    print '召回率字典长度 %d' % len(recall_num)

    true_positive = {}  # 真正例字典
    disease_dict = {}
    loop = 0
    for line in open("../data/i2025.txt", "r"):
        loop += 1
        if loop == 1:
            continue
        data = line.rstrip("\n").decode("UTF-8").split("\t")
        disease_dict[data[1]] = data[0]

    WRONG_FILE = "../res/bad_case" + str(num) + ".txt"
    RIGHT_FILE = "../res/good_case" + str(num) + ".txt"
    wrong_file = open(WRONG_FILE, "w")
    right_file = open(RIGHT_FILE, "w")
    correct, wrong, not_in, not_in_correct, not_in_wrong = 0, 0, 0, 0, 0
    for i, record in enumerate(open("../data/test.txt", "r")):
        x = record.rstrip("\n").decode("UTF-8").split("\t")
        for t in x:
            d = t.split("##")
            if d[1] == "NONE":
                continue
            if d[0] not in res:
                not_in += 1

                if init_res[d[0]] == d[1]:
                    if d[1] not in true_positive:
                        true_positive[d[1]] = 1
                    else:
                        true_positive[d[1]] += 1

                    correct += 1
                    not_in_correct += 1
                else:
                    wrong += 1
                    not_in_wrong += 1
                continue
            fuck, real_name = verdict(res[d[0]][0], d[1])
            if fuck:
                correct += 1
                if real_name not in true_positive:
                    true_positive[real_name] = 1
                else:
                    true_positive[real_name] += 1

                right_file.writelines(d[0] + " | " + res[d[0]][0] + " | " + str(res[d[0]][1]) + " | " + d[1] + "\n")
            else:
                wrong += 1
                wrong_file.writelines(d[0] + " | " + res[d[0]][0] + " | " + str(res[d[0]][1]) + " | " + d[1] + "\n")

    print "Correct %d" % correct
    print "Wrong %d" % wrong
    print "Not_in %d" % not_in
    print "Not_in_correct %d" % not_in_correct
    print "Not_in_wrong %d" % not_in_wrong
    print "Percent %.3f" % (correct * 1.0 / (correct + wrong))

    wrong_file.close()
    right_file.close()

    precision_num = cal_percent(true_positive, precision_num)
    recall_num = cal_percent(true_positive, recall_num)
    f1_num = f1(precision_num, recall_num)

    total_sum = sum(precision_num.values())
    total_sum /= len(precision_num)

    print '平均精确率 %.3f' % total_sum

    total_sum = sum(recall_num.values())
    total_sum /= len(recall_num)

    print '平均召回率 %.3f' % total_sum

    total_sum = sum(f1_num.values())
    total_sum /= len(f1_num)

    print '平均f1 %.3f' % total_sum


with open(NAME_DICT_FILE, "rb") as data_file:
    can_dic = cPickle.load(data_file)

with open(NO_CAND, "rb") as data_file:
    no_cand = cPickle.load(data_file)

test_init(can_dic, no_cand)
