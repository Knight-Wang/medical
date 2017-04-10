#!/usr/bin/env python
# -*- coding: utf-8 -*-
import jieba
import sys
import re
import pypinyin, Levenshtein
import MySQLdb
from util import loadDict
from sim_computation import *

reload(sys)
sys.setdefaultencoding('utf8')

#对诊断进行预处理，在分隔符处分开
def process(str):
    acronym = loadDict("./Dict/Acronym.txt") # 载入缩写字典
    keys = acronym.keys()

    #将缩写替换
    for k in keys:
        if str.find(k) != -1:
            str = re.sub(k, acronym[k], str)

    res_0 = str.replace('&nbsp;', ' ')
    res_0 = re.sub(ur"\u3000", ' ', res_0)   # 将中文的空格用英文空格代替，后面可以处理
    res_0 = re.sub(r"\w\d+.\d+", '', res_0) # 去除掉ICD编码 eg:I20.222
    res_0 = re.sub(r"\s\w+", "", res_0) #去掉空格后的字母，eg: 心肌梗塞急性 NOS

    #自定义的分隔符，分开
    seperator = ["病", "塞", "症", "痛"]
    for s in seperator:
        res_0 = re.sub(ur""+s, s + " ", res_0)

    # 用标点（（，："【】）*）进行切分
    res = re.split(ur"[（ ）\( \)， \.；;、：° \s+ \*\[ \] \+ ？? \,]", res_0)
    res = filter(lambda x: len(x) != 1 and len(x) != 0, res)

    return res

def addBrotherNodes(segs, name_dict, icd4_dic, icd6_dict):
    res = {}

    for name, sim in name_dict.iteritems():
        icd4 = icd6_dict[name][:5]
        res[name] = sim
        brothernodes = icd4_dic[icd4]

        for (brothernode,icd) in brothernodes:
            sim_b, contain_flag = sim_segs_entity(segs, brothernode)
            if sim_b >= 0.70 or contain_flag:
                res[brothernode] = sim_b
    return res

# 计算entity和mention的相似度，传入icd6的关键词字典为了考虑tfidf相似度
def sim_mention_entity(mention, e, icd6):
    contain_entity = False

    s_w = getWords(mention)
    e_w = getWords(e)
    intersect = set([p for p in s_w if p in e_w])
    s_p = pypinyin.lazy_pinyin(mention)
    t_p = pypinyin.lazy_pinyin(e)
    intersect_p = set([p for p in s_p if p in t_p])

    if mention.find(e) != -1 or len(intersect) == len(set(e_w)) or len(intersect_p) == len(set(t_p)):
        # 包含情况--
        # 1字面包含
        # 2字集合包含
        # 3拼音集合包含
        contain_entity = True

    sim_w = sim_words_tfidf(mention, e, icd6)  #字集合和tfidf的相似度
    sim_p = sim_pinyin(mention, e)  # 拼音的相似度
    sim_edit = edit_distance_sim(mention, e) # 编辑距离的相似度
    sim = max(sim_p, max(sim_w, sim_edit)) # 相似度取最大

    return sim, contain_entity

# 目前版本---考虑一个诊断包含多个疾病的情况，产生候选实体集合
def getMappingResult_segs(name_segs, normalized_dic): #return name, flag(compute_brother_nodes)
    seg_sim = []
    length = len(name_segs)
    name_all_str = "".join(name_segs)
    str_l = {}
    al_match_flag = [False] * length

    if length != 1 and name_all_str in normalized_dic.keys(): # 整体的精确匹配
        str_l[name_all_str] = 1
        seg_sim.append(str_l)
        return seg_sim

    for i in range(length): # 诊断的每个片段的匹配
        name_seg = name_segs[i] #诊断的片段
        this_seg_sim = dict()

        # 片段的精确匹配
        if name_seg in normalized_dic.keys():
            this_seg_sim[name_seg] = 1
            al_match_flag[i] = True

        # 判断待消歧疾病名称(mention)是否包含部位
        location_pattern = ur"[上下左右正前后侧][间壁室]+"
        location = re.findall(location_pattern, name_seg)

        if len(location) != 0:  # 存在部位
            unormalized_rm_seg = re.sub(ur"[上下左右正前后侧][间壁室]+", "", name_seg)

            for disease_name in normalized_dic.keys():
                icd6 = normalized_dic[disease_name]
                disease_name_location = re.findall(location_pattern, disease_name)
                disease_name_rm = disease_name # 去掉部位的标准疾病名称(entity)，若本身不包含部位，即为原标准疾病名

                if len(disease_name_location) != 0:
                    # disease_name_rm是去掉了部位的entity名称子串
                    disease_name_rm = re.sub(location_pattern, "", disease_name)
                    # entity和mention的部位的相似度
                    sim_location = compare_location(location, disease_name_location)
                else:
                    sim_location = -1

                # entity和mention的去掉部位的相似度
                sim_no_location, flag = sim_mention_entity(unormalized_rm_seg, disease_name_rm, icd6)

                #sim是综合sim_location和sim_no_location的相似度值
                sim = sim_no_location * 0.85 # 初始值--也是entity（标准疾病名称）不包含部位的情况下和去掉部位的mention的相似度值
                if sim_location != -1:
                    # sim = sim_location / 3 + 2 * sim_no_location / 3
                    sim = sim_location * 0.29 + 0.71 * sim_no_location

                contain_flag = determineContain(name_seg, disease_name) #判断name_seg是否包含了disease_name

                if sim >= 0.70 or contain_flag:
                # if sim >= 0.70: # 对比
                    this_seg_sim[disease_name] = sim
            al_match_flag[i] = True

        seg_sim.append(this_seg_sim) #每一个片段都有自己的候选实体集

    tmp = [{}] * length
    tmp_str = {}
    match_cases = [x for x in seg_sim if len(x) != 0]
    # if len(str_l) > 0 or length == 1 or len(match_cases) > 0: # 精确匹配成功 或 不需要从整体匹配
    if len(str_l) > 0 or length == 1: # 精确匹配成功 或 不需要从整体匹配
        need_str_edit_match = False
    else:
        need_str_edit_match = True

    seg_sim_names = {}
    for x in seg_sim:
        seg_sim_names.update(x)

    name_sets = list(set(normalized_dic.keys()) - set(seg_sim_names))
    for disease_name in name_sets:

        icd6 = normalized_dic[disease_name]
        if need_str_edit_match: #整体字符串的匹配
            str_sim, str_contain_d = sim_mention_entity(name_all_str, disease_name, icd6) # 对于整体字符串的情况
            if (str_contain_d and str_sim > 0.3) or str_sim >= 0.8:  # 半精确匹配
                str_l[disease_name] = str_sim

            elif str_sim >= 0.70:  # 模糊匹配,暂时不放入str_l中，在tmp中存
                tmp_str[disease_name] = str_sim

        for i in range(length):
            name_seg = name_segs[i]

            if al_match_flag[i] == False: # 说明精确匹配和部位的语义匹配未成功，进入半精确匹配和模糊匹配

                entity_location = re.findall(location_pattern, disease_name)
                if len(entity_location) > 0: #对于诊断不含部位，标准名称有部位的情况，直接跳过（因为肯定不映射成功）
                    continue

                # sim, contain_flag = sim_mention_entity(name_seg, disease_name)
                sim, contain_flag = sim_mention_entity(name_seg, disease_name, icd6 )

                if (contain_flag and sim >= 0.30) or sim >= 0.8: # 半精确匹配
                    seg_sim[i][disease_name] = sim

                elif sim >= 0.65: # 模糊匹配,暂时不放入seg_sim中，在tmp中存
                    tmp[i][disease_name] = sim

    for i in range(length):
        candidates = seg_sim[i]
        if len(candidates) == 0 and len(tmp[i]) != 0: # 只能放入模糊匹配的候选
            seg_sim[i] = tmp[i]

    if len(str_l) > 0:
        seg_sim.append(str_l)
    else:
        seg_sim.append(tmp_str)

    return seg_sim

# 之前版本---不考虑一个诊断包含多个疾病，产生一个诊断的候选实体集合
# return name, flag(compute_brother_nodes)
def getMappingResult(name_segs, normalized_dic, icd6_keywords):
    name_str = "".join(name_segs)
    res = dict()

    # 精确匹配
    if name_str in normalized_dic.keys():
        res[name_str] = 1
        return res, 1

    # 判断待消歧疾病名称(mention)是否包含部位
    location_pattern = ur"[上下左右正前后侧][间壁室]+"
    location = re.findall(location_pattern, name_str)

    if len(location) != 0:  # 存在部位
        unormalized_rm_segs = remove_location(name_segs)

        for disease_name in normalized_dic.keys():
            # keywords = icd6_keywords[normalized_dic[disease_name]]
            # k_sim = keyword_sim(name_str, keywords)

            disease_name_location = re.findall(location_pattern, disease_name)
            disease_name_rm = disease_name # 去掉部位的标准疾病名称(entity)，若本身不包含部位，即为原标准疾病名

            if len(disease_name_location) != 0:
                # disease_name_rm是去掉了部位的entity名称子串
                disease_name_rm = re.sub(location_pattern, "", disease_name)
                # entity和mention的部位的相似度
                sim_location = compare_location(location, disease_name_location)
            else:
                sim_location = -1

            # entity和mention的去掉部位的相似度
            sim_no_location, contain_flag = sim_segs_entity(unormalized_rm_segs, disease_name_rm)

            #sim是综合sim_location和sim_no_location的相似度值
            sim = sim_no_location * 0.85 # 初始值--也是entity（标准疾病名称）不包含部位的情况下和去掉部位的mention的相似度值
            if sim_location != -1:
                # sim = sim_location / 3 + 2 * sim_no_location / 3
                sim = sim_location * 0.29 + 0.71 * sim_no_location

            contain_flag = determineContain(name_str, disease_name) #必须重新赋值，因为前面213行计算的是不包括部位的包含情况

            if sim >= 0.70 or contain_flag:
            # if sim >= 0.70:#对比
                res[disease_name] = sim
        return res, 3 # 基于部位的语义匹配

    res_find = {}
    for disease_name in normalized_dic.keys():

        # keywords = icd6_keywords[normalized_dic[disease_name]]
        entity_location = re.findall(location_pattern, disease_name)
        if len(entity_location) > 0: #对于诊断不含部位，标准名称有部位的情况，直接跳过（因为肯定不映射成功）
            continue

        sim, contain_flag = sim_segs_entity(name_segs, disease_name)
        # sim, contain_flag = sim_segs_entity(name_segs, disease_name, keywords)

        if name_str.find(disease_name) != -1 or contain_flag or sim >= 0.8: # 半精确匹配
            res_find[disease_name] = sim

        elif sim >= 0.62: # 模糊匹配
            res[disease_name] = sim

    if len(res_find) != 0:
        # 如果在半精确匹配中加入了模糊匹配，会引入大量干扰情况，但对于少量拆分情况，会有提升，如：心绞痛，不稳定性
        for (k,v) in res.items():
            if v >= 0.68:
                res_find[k] = v
        return res_find, 2 # 半精确匹配

    return res, 4   # 模糊匹配

# 之前版本--不考虑一个诊断包含多个疾病的情况：一个诊断分为几个片段（segments）,片段集合和entity进行相似度匹配
def sim_segs_entity(segs, e):

    name_str = "".join(segs)
    contain_entity = False

    sp = pypinyin.lazy_pinyin(name_str)
    tp = pypinyin.lazy_pinyin(e)
    intersect_p = set([p for p in sp if p in tp])

    sp_str = "".join(sp)
    tp_str = "".join(tp)

    s_w = getWords(name_str)
    e_w = getWords(e)
    intersect = [p for p in s_w if p in e_w]

    if sp_str.find(tp_str) != -1 or len(intersect) == len(e_w) or len(intersect_p) == len(tp):
        contain_entity = True
    sim_all_w = sim_words(name_str, e)
    sim_all_p = sim_pinyin(name_str, e)
    sim_s = max(sim_all_p, sim_all_w)

    sim_seg_w = 0
    sim_seg_p = 0
    for seg in segs:
        sim_seg_w = max(edit_distance_sim(seg, e), sim_seg_w)
        sim_seg_p = max(sim_pinyin(seg, e), sim_seg_p)

    sim = max(sim_s, max(sim_seg_p, sim_seg_w))
    return sim, contain_entity
