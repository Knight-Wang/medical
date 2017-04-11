#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pypinyin, re, jieba, pickle
from scipy import spatial
from sklearn.externals import joblib
from sklearn.feature_extraction.text import TfidfVectorizer, TfidfTransformer,CountVectorizer
from util import loadICD_Keywords_Dict, loadICD_Keywords_Set

class sim_computation:

    # 方向性的编辑距离计算，将插入的惩罚加大
    def edit_distance_sim(self, s, t):
        m, n = len(s), len(t)
        dist = [[0.0 for j in range(n + 1)] for i in range(m + 1)]

        for i in range(1, m + 1):
            dist[i][0] = i * 2.0
        for j in range(1, n + 1):
            dist[0][j] = j * 2.0

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s[i - 1] == t[j - 1]:
                    dist[i][j] = dist[i - 1][j - 1]
                else:
                    dist[i][j] = min(dist[i - 1][j] + 1,  # t delete a char
                                     dist[i][j - 1] + 2.0,  # t insert a char
                                     dist[i - 1][j - 1] + 1)  # t substitute a char
        return 1.0 - float(dist[m][n]) / max(m, n)

    # 得到字集合
    def getWords(self, str):
        str_u = str.decode("utf-8")
        res = set()
        for i in str_u:
            res.add(i)
        return res

    # 字集合的相似度
    def sim_words(self, s, t):
        sw = self.getWords(s)
        tw = self.getWords(t)
        sim = float(len(sw & tw)) / float(max(len(sw), len(tw)))
        return sim

    # 部位的相似度计算，计算交集/并集
    def compare_location(self, l1, l2):

        inter = [x for x in l1 if x in l2]
        return float(len(inter)) / len(l1)

    # 将诊断去除部位
    def remove_location(self, segs):
        res = []
        for seg in segs:
            seg_ = re.sub(ur"[上下左右正前后侧][间壁室]+", "", seg)
            res.append(seg_)
        return res

    # 判断target中是否包含pattern字符串，基于字符串的字面包含和字集合的包含
    def determineContain(self, target, pattern):
        if target.find(pattern) != -1:
            flag = True
        else:
            tar_w = self.getWords(target)
            pattern_w = self.getWords(pattern)
            intersect_set = [p for p in tar_w if p in pattern_w]
            if len(intersect_set) == len(pattern_w):
                flag = True
            else:
                flag = False
        return flag

    # 基于拼音的字符串的相似度计算
    def sim_pinyin(self, s,t):
        sp = pypinyin.lazy_pinyin(s)
        tp = pypinyin.lazy_pinyin(t)

        if abs(len(sp)-len(tp)) >= 4: # 针对诊断较长的情况，用拼音的词集合
                intersection = [x for x in tp if x in sp]
                sim = float(len(intersection)) / float(max(len(sp), len(tp)))
        else:
            sim = self.Levenshtein_distance_pinyin(sp, tp)
        return sim

    # 拼音字符串的编辑距离计算
    def Levenshtein_distance_pinyin(self, s, t):
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

    # 基于tfidf的相似度计算
    def sim_words_tfidf(self, s, t, icd6, tfidf_dict):
            sw = self.getWords(s)
            tw = self.getWords(t)

            icd6_keywords = loadICD_Keywords_Dict()

            t_words = icd6_keywords[icd6]
            words = loadICD_Keywords_Set()
            t_vector = []
            s_segs_tfidf = tfidf_dict.transform([" ".join(list(jieba.cut(s)))]).todense() # change from sparse matrix to vector

            t_words_entity = [t for (t, v) in t_words]
            t_words_tfidf = [v for (t, v) in t_words]

            for word in words:

                if word in t_words_entity:
                    value = t_words_tfidf[t_words_entity.index(word)]
                    t_vector.append(value)
                else:
                    t_vector.append(0.0)

            if s_segs_tfidf.sum() == 0: # 均匹配不上
                sim_tfidf = 0
            else:
                sim_tfidf = 1 - spatial.distance.cosine(s_segs_tfidf, t_vector)  # cosine similarity

            sim_w = float(len(sw & tw)) / float(max(len(sw), len(tw)))
            sim = max(sim_tfidf, sim_w)
            return sim
