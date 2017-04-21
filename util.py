#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')

def getICD3Tree(normal):
    icd3_dict = {}

    for name, icd6 in normal.iteritems():
        icd3 = icd6[:3]
        if icd3 not in icd3_dict.keys():
            icd3_dict[icd3] = [(name, icd6)]
        else:
            icd3_dict[icd3].append((name, icd6))
    return icd3_dict

# 载入ICD层次结构，返回的字典，键是icd4位码，值是list，list中每元素为(ICD6_name, icd6)
def getICDTree(normal):
    icd4_dict = {}

    for name, icd6 in normal.iteritems():
        icd4 = icd6[:5]
        if icd4 not in icd4_dict.keys():
            icd4_dict[icd4] = [(name, icd6)]
        else:
            icd4_dict[icd4].append((name, icd6))
    return icd4_dict

# 载入字典（缩写字典）
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

# 载入icd6的关键词集合，已去重
def loadICD_Keywords_Dict():
    file = open("./Dict/ICD_Keywords_Dict.txt")
    line = file.readline()
    res = {}

    while(line != ""):
        icd = line.split("-")[0]
        words = line.split("-")[1].split(",")
        key_words = []
        for str in words:
            key_words.append((str.split(":")[0], float(str.split(":")[1])))
        res[icd] = key_words
        line = file.readline()
    return res

def getNormalNames(values):
    normal = {}  # 标准疾病名称字典(normalized_name, ICD-10)

    for row in values:
        if isinstance(row[0], unicode):
            normal[row[1].decode('utf-8')] = row[0].decode('utf-8')
    return normal

def write_List(file, names):
    file.write(" | ".join(names) + "\n")