#!/usr/bin/env python
# -*- coding: utf-8 -*-

import MySQLdb
import sys
import datetime
import re
import  os

reload(sys)
sys.setdefaultencoding('utf8')

def process (str):
    res = str.replace('&nbsp;', '')
    #res = res.replace('?', '')
    #res = res.replace('？', '')
    # res = re.split('\(|\)| |\*|（|）|\[|\]|【|】|,|，|、|;|；', res) #用标点（（，："【】）*）进行切分
    res = re.split(r'[\（, \）,，, ., ;,：, \s, \*，\[, \], +,?]\s*', res) #用标点（（，："【】）*）进行切分
    return filter(lambda x: len(x) != 1 and len(x) != 0, res)

def otherForm(s): # consider the alias dictionary(waiting to be detailed)
    res = list()
    if s.find("型") != -1:
        res.append(s.replace("型", "性"))
    if s.find("性") != -1:
        res.append(s.replace("性", "型"))
    if s.find("塞") != -1:
        res.append(s.replace("塞", "死"))
    if s.find("死") != -1:
        res.append(s.replace("死", "塞"))
    return res

def getWords(str):
    str_u = str.decode("utf-8")
    res = set()
    for i in str_u:
        res.add(i)
    return res

def getMappingResult(name_segs, normalized_dic): #return name
    name_str = "".join(name_segs)
    res = set()

    for seg in name_segs:
        #could be optimized...
        for disease_name in normalized_dic.keys():
            # 完全匹配
            if seg.find(disease_name) != -1:
                res.add(disease_name)

            # deal with alias of disease names(such as 型VS性)
            disease_name_alias = otherForm(disease_name)
            for n_a in disease_name_alias:
                if seg.find(n_a) != -1:
                    res.add(disease_name)
    # if len(res) != 0:
    #     return res
    # including relationship in word aspects
    description_words = getWords(name_str)

    for disease_name in normalized_dic.keys():
        n_words = getWords(disease_name)
        disease_name_alias = otherForm(disease_name)

        #normalized disease entity may include in the description
        if len(n_words) == len(n_words & description_words):
                res.add(disease_name)

        #alias disease name may include in the dscription
        for n_alias in disease_name_alias:
              n_alias_words = getWords(n_alias)
              len_intersection = len(n_alias_words & description_words)
              if len(n_alias_words) ==  len_intersection or len(name_str) == len_intersection :
                   res.add(disease_name)
                   break
    return res

def getNormalNames(values):
    normal = {}  # 标准疾病名称字典(normalized_name, ICD-10)

    for row in values:
        if isinstance(row[0], unicode):
            normal[row[1].decode('utf-8')] = row[0].decode('utf-8')
    return normal

def writeFile(file, unormalized, u_id, normalized, n_id):
    file.write(unormalized + " | " + u_id + " | " + normalized + " | " + n_id + "\n")