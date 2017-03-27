#!/usr/bin/env python
# -*- coding: utf-8 -*-
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
import sys
import re
import pypinyin, Levenshtein

reload(sys)
sys.setdefaultencoding('utf8')

def getFeatureEntity(normal): #normal(entity, ICD10)
    features = {}
    corpus = []
    icd_list = []
    jieba.set_dictionary('./Dict/my_dict.txt')

    for (e, icd) in normal.iteritems():
        segs = jieba.cut(e)
        icd_list.append(icd)
        corpus.append(" ".join(segs))

    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(corpus)
    words = vectorizer.get_feature_names()
    i = 0
    for icd in icd_list:
        keywords = {}

        for j in xrange(len(words)):
            if tfidf[i,j] > 0:
                keywords[words[j].encode('utf-8')] = tfidf[i,j]
        features[icd] = keywords
        i += 1

    return features

def loadICD6Features(normal):
    icd3_dic = getICD3Tree(normal)
    res = {}

    for icd3, names in icd3_dic.iteritems():
        names_dic = {}
        for (k, v) in names:
            names_dic[k] = v
        res = getFeatureEntity(names_dic)
        for (k, v) in res.iteritems():
            res[k] = sorted(v.items(), key=lambda e: e[1], reverse=True)
    return res

def keyword_sim(mention_str,keywords):
    sum_v = 0
    sim = 0
    # keywords = icd6_keywords[icd]
    for (k, v) in keywords:
            sum_v += v
            if k in mention_str:
                sim += v
    sim /= sum_v
    return sim

def loadDict(filename):
    file = open(filename)
    res = {}

    while 1:
        line = file.readline().strip()
        if not line:
            break

        n1 = line.split(" ")[0]
        n2 = line.split(" ")[1]
        res[n1.decode("utf-8")] = n2.decode("utf-8")
        res[n2.decode("utf-8")] = n1.decode("utf-8")
    return res

def process(str):
    acronym = loadDict("./Dict/Acronym.txt") # 载入缩写字典
    keys = acronym.keys()

    for k in keys:
        if str.find(k) != -1:
            str = re.sub(k, acronym[k], str)

    res_0 = str.replace('&nbsp;', ' ')
    res_0 = re.sub(ur"\u3000",' ', res_0)   # 将中文的空格用英文空格代替，后面可以处理
    res_0 = re.sub(r"\w\d+.\d+", '', res_0) # 去除掉ICD编码 eg:I20.222
    res_0 = re.sub(r"\s\w+", "", res_0) #去掉空格后的字母，eg: 心肌梗塞急性 NOS

    seperator = ["病", "塞", "死", "症", "痛"]
    for s in seperator:
        res_0 = re.sub(ur""+s, s + " ", res_0)

    res = re.split(ur"[（ ）\( \)， \.；;、：° \s+ \*\[ \] \+ ？? \,]", res_0)  # 用标点（（，："【】）*）进行切分
    res = filter(lambda x: len(x) != 1 and len(x) != 0, res)

    return res

def getWords(str):
    str_u = str.decode("utf-8")
    res = set()
    for i in str_u:
        res.add(i)
    return res

def getICDTree(normal):
    icd4_dict = {}

    for name, icd6 in normal.iteritems():
        icd4 = icd6[:5]
        if icd4 not in icd4_dict.keys():
            icd4_dict[icd4] = [(name, icd6)]
        else:
            icd4_dict[icd4].append((name, icd6))
    return icd4_dict

def getICD3Tree(normal):
    icd3_dict = {}

    for name, icd6 in normal.iteritems():
        icd3 = icd6[:3]
        if icd3 not in icd3_dict.keys():
            icd3_dict[icd3] = [(name, icd6)]
        else:
            icd3_dict[icd3].append((name, icd6))
    return icd3_dict

def addBrotherNodes(segs, name_dict, icd4_dic, icd6_dict , icd6_keywords):
    res = {}

    for name, sim in name_dict.iteritems():
        icd4 = icd6_dict[name][:5]
        res[name] = sim
        keywords = icd6_keywords[icd6_dict[name]]
        brothernodes = icd4_dic[icd4]

        for (brothernode,icd) in brothernodes:
            sim_b, contain_flag = sim_segs_entity(segs, brothernode)
            if sim_b >= 0.70 or contain_flag:
                res[brothernode] = sim_b
    return res

# def addFatherAndBrotherNodes(segs, name_dict, icd3_dic, icd4_dic, icd6_dict , icd6_keywords):
#     res = {}
#
#     for name, sim in name_dict.iteritems():
#         icd4 = icd6_dict[name][:5]
#         icd3 = icd4[:3]
#         res[name] = sim
#
#         father_node = icd3_dic[icd3]
#         sim_f, contain_flag = sim_segs_entity(segs, father_node, icd6_keywords)
#
#         res[father_node] = sim_f
#
#         brothernodes = icd4_dic[icd4]
#
#         for (brothernode,icd) in brothernodes:
#             sim_b, contain_flag = sim_segs_entity(segs, brothernode, icd6_keywords)
#             if sim_b >= 0.70 or contain_flag:
#                 res[brothernode] = sim_b
#     return res

# def addFatherNode(segs, name_dict, icd3_dic, icd6_dict, icd6_keywords):
#     res = {}
#
#     for name, sim in name_dict.iteritems():
#         icd4 = icd6_dict[name][:5]
#         icd3 = icd4[:3]
#         res[name] = sim
#
#         father_node = icd3_dic[icd3]
#         sim_f, contain_flag = sim_segs_entity(segs, father_node, icd6_keywords)
#         res[father_node] = sim_f
#
#     return res

# def sim_segs_entity(segs, e, keywords):
#
#     name_str = "".join(segs)
#     contain_entity = False
#     k_sim = keyword_sim(name_str, keywords)
#
#     sp = pypinyin.lazy_pinyin(name_str)
#     tp = pypinyin.lazy_pinyin(e)
#
#     sp_str = "".join(sp)
#     tp_str = "".join(tp)
#
#     s_w = getWords(name_str)
#     e_w = getWords(e)
#     intersect = [p for p in s_w if p in e_w]
#
#     if sp_str.find(tp_str) != -1 or len(intersect) == len(e_w):
#         contain_entity = True
#     sim_s = max(sim_words(name_str, e), sim_pinyin(name_str, e))
#
#     sim_seg_w = 0
#     sim_seg_p = 0
#     for seg in segs:
#         sim_seg_w = max(Levenshtein.ratio(seg, e), sim_seg_w)
#         sim_seg_p = max(sim_pinyin(seg, e), sim_seg_p)
#
#     # sim = max(max(sim_s, max(sim_seg_p, sim_seg_w)),k_sim)
#     sim = max(sim_s, max(sim_seg_p, sim_seg_w))
#     return sim, contain_entity

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
    # if sp_str.find(tp_str) != -1 or len(intersect) >= 0.8 * len(e_w):
        contain_entity = True
    sim_all_w = sim_words(name_str, e)
    sim_all_p = sim_pinyin(name_str, e)
    sim_s = max(sim_all_p,sim_all_w )

    sim_seg_w = 0
    sim_seg_p = 0
    for seg in segs:
        sim_seg_w = max(Levenshtein.ratio(seg, e), sim_seg_w)
        sim_seg_p = max(sim_pinyin(seg, e), sim_seg_p)

    # sim = max(max(sim_s, max(sim_seg_p, sim_seg_w)),k_sim)
    sim = max(sim_s, max(sim_seg_p, sim_seg_w))
    return sim, contain_entity

def compare_location(l1, l2):

    inter = [x for x in l1 if x in l2]
    return float(len(inter)) / len(l1)

def remove_location(segs):
    res = []
    for seg in segs:
        seg_ = re.sub(ur"[上下左右正前后侧][间壁室]+", "", seg)
        res.append(seg_)
    return res

def determineContain(target, pattern):
    if target.find(pattern) != -1:
        flag = True
    else:
        tar_w = getWords(target)
        pattern_w = getWords(pattern)
        intersect_set = [p for p in tar_w if p in pattern_w]
        if len(intersect_set) == len(pattern_w):
            flag = True
        else:
            flag = False
    return flag

def getMappingResult(name_segs, normalized_dic, icd6_keywords): #return name, flag(compute_brother_nodes)
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

            # sim = sim * 0.9 + 0.1 * k_sim

            if sim >= 0.70 or contain_flag:
            # if sim >= 0.70:#对比
                res[disease_name] = sim
        return res, 3 # 基于部位的语义匹配

    res_find = {}
    for disease_name in normalized_dic.keys():
        # if disease_name == "不稳定性心绞痛":
        #     print("")
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
        for (k,v) in res.items(): #如果在半精确匹配中加入了模糊匹配，会引入大量干扰情况，但对于少量拆分情况，会有提升，如：心绞痛，不稳定性
            if v >= 0.68:
                res_find[k] = v
        return res_find, 2 # 半精确匹配

    return res, 4   # 模糊匹配

def sim_words(s,t):
    sw = getWords(s)
    tw = getWords(t)
    sim = float(len(sw & tw)) / float(max(len(sw), len(tw)))
    # sim = float(len(sw & tw)) / float(len(tw))
    return sim

def sim_pinyin(s,t):
    sp = pypinyin.lazy_pinyin(s)
    tp = pypinyin.lazy_pinyin(t)

    if abs(len(sp)-len(tp)) >= 4: # 针对诊断较长的情况，用拼音的词集合
            intersection = [x for x in tp if x in sp]
            sim = float(len(intersection)) / float(max(len(sp), len(tp)))
    else:
        sim = Levenshtein_distance_pinyin(sp, tp)
    return sim

def Levenshtein_distance_pinyin(s, t):
    m,n = len(s), len(t)
    dist = [[0.0 for j in range(n+1)] for i in range(m + 1)]

    for i in range(1, m + 1):
        dist[i][0] = i * 1.0
    for j in range(1, n + 1):
        dist[0][j] = j * 1.0

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dist[i][j] = dist[i - 1][j - 1]
            else:
                # 拼音的第一个音如果相同，cost减小一些，为的是处理"塞"VS"死"的问题
                if s[i-1][0] == t[j-1][0]:
                    cost = 0.5
                else:
                    cost = 1
                dist[i][j] = min(dist[i - 1][j] + 1.0,  # t delete a char
                              dist[i][j - 1] + 1.0,  # t insert a char
                              dist[i - 1][j - 1] + cost)  # t substitute a char
    return 1.0 - float(dist[m][n])/max(m,n)

def getNormalNames(values):
    normal = {}  # 标准疾病名称字典(normalized_name, ICD-10)

    for row in values:
        if isinstance(row[0], unicode):
            normal[row[1].decode('utf-8')] = row[0].decode('utf-8')
    return normal

def getTieTops(sortnamelist):
    length = len(sortnamelist)
    res = [sortnamelist[0]]
    top_sim = sortnamelist[0][1]

    for i in range(1, length):
        if top_sim == sortnamelist[i][1]: #Tie top 1
            res.append(sortnamelist[i])
        else:
            break
    return res

def optimizeTopCandidates(name_sim_list, icd3_names, entity_icd_map):
    length = len(name_sim_list)
    name_list = [name for(name, sim) in name_sim_list]
    delete_name = []

    for i in range(length):
        icd3 = entity_icd_map[name_list[i]][:3]
        if(icd3_names[icd3] in name_list): # 父节点和子节点同时出现在候选实体集合中，删去父节点
            delete_name.append(icd3_names[icd3])
    return [(name, sim) for (name, sim) in name_sim_list if name not in delete_name]

def writeFile(file, unormalized, u_id, normalized, n_id):
    file.write(unormalized + " | " + u_id + " | " + normalized + " | " + n_id + "\n")