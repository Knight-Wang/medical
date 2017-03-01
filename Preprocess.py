#!/usr/bin/env python
# -*- coding: utf-8 -*-

import MySQLdb
import sys
import datetime
import re
import os
import pypinyin, Levenshtein

reload(sys)
sys.setdefaultencoding('utf8')


def process(str):
    res = str.replace('&nbsp;', '')
    # res = res.replace('?', '')
    # res = res.replace('？', '')
    # res = re.split('\(|\)| |\*|（|）|\[|\]|【|】|,|，|、|;|；', res) #用标点（（，："【】）*）进行切分
    res = re.split(ur"[（ ）\( \)， \. ;、： \s+ \*\[ \] \+ ？? \,]", res) #用标点（（，："【】）*）进行切分
    return filter(lambda x: len(x) != 1 and len(x) != 0, res)

#
# def otherForm(s): # consider the alias dictionary(waiting to be detailed)
#     res = list()
#     if s.find("型") != -1:
#         res.append(s.replace("型", "性"))
#     if s.find("性") != -1:
#         res.append(s.replace("性", "型"))
#     if s.find("塞") != -1:
#         res.append(s.replace("塞", "死"))
#     if s.find("死") != -1:
#         res.append(s.replace("死", "塞"))
#     return res

def getWords(str):
    str_u = str.decode("utf-8")
    res = set()
    for i in str_u:
        res.add(i)
    return res


def getMappingResult(name_segs, normalized_dic): #return name
    name_str = "".join(name_segs)
    res = dict()

    # for seg in name_segs:
    #     #could be optimized...
    #     for disease_name in normalized_dic.keys():
    #         # 完全匹配
    #         if seg.find(disease_name) != -1:
    #             res.add(disease_name)
    #
    #         # deal with alias of disease names(such as 型VS性)
    #         disease_name_alias = otherForm(disease_name)
    #         for n_a in disease_name_alias:
    #             if seg.find(n_a) != -1:
    #                 res.add(disease_name)

    for disease_name in normalized_dic.keys():

        # 可能seg并不包括完整的疾病名称，因此先将整个字符串和标准名称对比
        sim = sim_words(name_str, disease_name)
        if sim >= 0.75:
            res[disease_name] = sim
            continue

        sim_p = sim_pinyin(name_str, disease_name)
        if sim_p >= 0.75:
            res[disease_name] = sim_p
            continue

        #完整诊断是否包含标准疾病名称
        if name_str.find(disease_name) != -1:
            res[disease_name] = 0.9

        else:
            #对分隔开的诊断片段判断和标准疾病的相似度
            for seg in name_segs:
                sim = sim_words(seg, disease_name)
                if sim >= 0.75:
                    res[disease_name] = sim
                    continue

                sim_p = sim_pinyin(seg, disease_name)
                if sim_p >= 0.75:
                    res[disease_name] = sim_p
                    continue
    return res

def sim_words(s,t):
    sw = getWords(s)
    tw = getWords(t)
    sim = float(len(sw & tw)) / float(max(len(sw), len(tw)))
    return sim

def sim_pinyin(s,t):
    sp = "".join(pypinyin.lazy_pinyin(s))
    tp = "".join(pypinyin.lazy_pinyin(t))
    sim = Levenshtein.ratio(sp, tp)
    return sim

def getNormalNames(values):
    normal = {}  # 标准疾病名称字典(normalized_name, ICD-10)

    for row in values:
        if isinstance(row[0], unicode):
            normal[row[1].decode('utf-8')] = row[0].decode('utf-8')
    return normal


def writeFile(file, unormalized, u_id, normalized, n_id):
    file.write(unormalized + " | " + u_id + " | " + normalized + " | " + n_id + "\n")