#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import copy
reload(sys)
sys.setdefaultencoding('utf8')

#从label数据集中得到疾病的先验概率
def getPriorProb(rows):
    prob = {}
    sum = len(rows)

    for row in rows:
        normalized_name = row[2].strip()
        if normalized_name not in prob.keys():
            prob[normalized_name] = 0.0
        prob[normalized_name] += 1.0

    for (k, v) in prob.iteritems():
        prob[k] /= sum
    return prob

# 将并列相似度的实体加入res返回
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

# 父节点和子节点同时出现在候选实体集合中，删去父节点
def optimizeTopCandidates(name_sim_list, icd3_names, entity_icd_map):

    length = len(name_sim_list)
    name_list = [name for(name, sim) in name_sim_list if name != ""]
    delete_name = []

    for i in range(length):
            icd3 = entity_icd_map[name_list[i]][:3]
            father_node = icd3_names[icd3]
            if(name_list[i] != father_node and father_node in name_list):
                delete_name.append(father_node)
    res = [(name, sim) for (name, sim) in name_sim_list if name not in delete_name]

    if len(res) == 0: #说明集合中的都是父节点，返回集合
        return name_sim_list
    else:
        return res

# 设字符串有n个segment，返回(n + 1)个top candidates
# 返回每个segment的top1候选实体，加上整个字符串匹配时的top1候选实体
def getTopCandidate(seg_dict,  p_name, tfidfdict):

    segs_top_list = []

    p_name_copy = copy.deepcopy(p_name)
    p_name_copy.append("".join(p_name))

    i = 0
    for seg_candidate in seg_dict:
        if len(seg_candidate) == 0: # 某segment的候选实体集合为空时，seg_top 为""
            seg_top = ""
        else:
            #取每个segment的候选实体集合的top1
            k = min(len(seg_candidate), 5)
            seg_top_set = sorted(seg_candidate.iteritems(), key= lambda x: x[1], reverse=True)[:k] #top candidate( name ,sim)

            other_w = []
            match = False
            # according to tfidf, sort the candidates for each segment
            for (name, sim) in seg_top_set:
                words = tfidfdict[str(name)]
                other_w = [w for w in words if w not in p_name_copy[i]]
                if (len(other_w) == 1 and sim > 0.85) or len(other_w) == 0 :
                    match = True
                    break
            if match == True:
                seg_top = name
            else:
                seg_top = seg_top_set[0][0]
            # for (n, s) in seg_top:
            #     if s == seg_top[1]: # Tie situation
            #         segs_top_list.append((n,s))
            #     else:
            #         break
            #TO DO

        segs_top_list.append(seg_top)
        i += 1
    return segs_top_list

def basicDisambiguation_top1(top_candidate, priorProb, icd3_names, normal):
    # top1 disambiguation
    # 分段的候选实体集和的top1产生：
    # （每个segment的候选实体集合 + 整体匹配的候选实体集合）的top1的集合是top_candidate，用先验概率进行排序，选取top1
    tmp = {}
    length = len(top_candidate)

    if length != 0:
        # top 1
        need_complete = 0
        for i in range(length - 1):
                (k, v) = top_candidate[i]
                if k != "":
                    if k in priorProb:
                        tmp[k] = priorProb[k]
                    else:
                        tmp[k] = 0.0
                if v >= 0.90:
                    need_complete += 1

        if need_complete == 0:
        # 当片段的top1实体的相似度都小于0.9时，需要加入整体字符串的候选实体集中的top1实体
        # 否则，不用加入整体字符串的候选实体集中的top1实体，因为会引入噪音
            (k, v) = top_candidate[length - 1]
            if k != "":
                if k in priorProb:
                    tmp[k] = priorProb[k]
                else:
                    tmp[k] = 0.0

        if len(tmp) != 0:
            res = sorted(tmp.iteritems(), key=lambda x:x[1],reverse=True)
            res = optimizeTopCandidates(res, icd3_names, normal) # 父节点和子节点同时出现在候选实体集合中，删去父节点
            return res[0][0]
    return ""

# topK的消歧，是基于最初（没有分段（每segment有候选实体集合））的候选实体集和排序。
def basicDisambiguation(sort_name_list, len_candidates, topK,icd3_names, normal, alias_dict ):

    if len_candidates != 0:

        candidate_top_k = []

        # topK
        if len_candidates >= topK:
            if topK != 1:
                candidate_top_k = [sort_name_list[i][0] for i in range(topK)]
            else:
                # top 1

                tie_tops = getTieTops(sort_name_list)
                if (len(tie_tops) > 1):
                    tie_tops = optimizeTopCandidates(tie_tops, icd3_names, normal)
                candidate_top_k.append(tie_tops[0][0])

                if tie_tops[0][0] in alias_dict.keys():  # 别名情况下，两个疾病的相似度相同
                    candidate_top_k.append(alias_dict[tie_tops[0][0]])
        else:
            candidate_top_k = [sort_name_list[i][0] for i in range(len_candidates)]
    return candidate_top_k