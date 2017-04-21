#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 将六位码的字典切分作为关键词字典，保存在./Dict/icd6_seg.txt中
# 因为用tfidf切分提取标准疾病字典的关键词速度太慢，所以用最朴素的这个。

import jieba
from util import getICD_file


icd6 = getICD_file("./Dict/Norm6.csv", "\t")
file = open("./Dict/icd6_seg.txt", "w+")

for (icd, name) in icd6:
    jieba.load_userdict("./Dict/my_dict.txt")
    # name = list(jieba.cut(name))
    tmp = list(jieba.cut(name))
    seg_name = [t for t in tmp if len(t) > 1]
    file.write(icd + ":" + " ".join(seg_name) + ":" + name + "\n")
