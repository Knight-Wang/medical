#!/usr/bin/env python
# coding=utf-8

from Preprocess import *
from util import getNormalNames, loadDict
import copy
import MySQLdb

class candidate_sim_generator():

    def __init__(self):
        conn = MySQLdb.connect("localhost", "root", "10081008", "medical", charset='utf8')
        cursor = conn.cursor()
        cursor.execute('select ICD,疾病名称 from I2025')
        values = cursor.fetchall()
        self.normal = getNormalNames(values)  # (normalized_name, ICD-10)
        self.tfidf = pickle.load(open("vectorizerTFIDF.pickle", "rb"))

        self.alias_dict = loadDict("./Dict/Alias.txt")

    # 返回候选实体集合
    # is_single_segment = 1 说明诊断只有一个片段
    # is_single_segment = 0 说明诊断有多个片段
    def getCandidates(self, names_segs):

        name_dict_seg = getMappingResult_segs(names_segs, self.normal, self.tfidf)
        is_single_segment = 1 if len(names_segs) == 1 else 0

        # add alias
        segments_len = len(name_dict_seg)
        dict_copy = copy.deepcopy(name_dict_seg)
        for i in range(segments_len):
            for (k, v) in dict_copy[i].iteritems():
                if k in self.alias_dict.keys():
                    name_dict_seg[i][self.alias_dict[k]] = v

        return is_single_segment, name_dict_seg
