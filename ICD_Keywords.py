#!/usr/bin/env python
# -*- coding: utf-8 -*-
import jieba
import sys
import re
import MySQLdb, pickle
from sklearn.externals import joblib
from Preprocess import *
from util import getICD3Tree, getNormalNames
from sklearn.feature_extraction.text import TfidfVectorizer

# 用TF-iDF生成标准疾病字典中的关键词，存入文件中
class ICD_Keywords:

    keywords_set_file = "./Dict/ICD_Keywords_Dict.txt"

    def getFeatureEntity(self, normal): #normal(entity, ICD10)
        features = {}
        corpus = []
        icd_list = []
        jieba.set_dictionary('./Dict/my_dict.txt') # load self-defined dictionary

        for (e, icd) in normal.iteritems():
            segs = jieba.cut(e)
            icd_list.append(icd)
            corpus.append(" ".join(segs))

        #TF-IDF to get keywords of each entity in normalized dictionary
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform(corpus)

        # Save vectorizer.vocabulary_
        with open('vectorizerTFIDF.pickle', 'wb') as idxf:
            pickle.dump(vectorizer, idxf, pickle.HIGHEST_PROTOCOL)

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

    # load in keywords of icd6 dict and keywords_set
    def loadICD6Features(self, normal):
        icd3_dic = getICD3Tree(normal)
        result = {}
        keywords = []

        names_dic = {}
        for icd3, names in icd3_dic.iteritems():
            for (k, v) in names:
                names_dic[k] = v
        res = self.getFeatureEntity(names_dic)


        # # 每一个三位码当做一个corpus，用tf-idf模型计算
        # for icd3, names in icd3_dic.iteritems():
        #     names_dic = {}
        #     for (k, v) in names:
        #         names_dic[k] = v
        #     res = self.getFeatureEntity(names_dic)
            # for (k, v) in res.iteritems():
            #     result[k] = sorted(v.items(), key=lambda e: e[1], reverse=True)
            #     keywords.extend(v.keys())
        return res
        # return result, set(keywords)

    def writeInFile_Dict(self):
        reload(sys)
        sys.setdefaultencoding('utf8')

        conn = MySQLdb.connect("localhost", "root", "10081008", "medical", charset='utf8')
        cursor = conn.cursor()

        cursor.execute('select ICD,疾病名称 from I2025')
        values = cursor.fetchall()
        normal = getNormalNames(values)  # (normalized_name, ICD-10)

        icd6_keywords = self.loadICD6Features(normal)  # (icd6, keywords dict)
        # icd6_keywords, keywords_set = self.loadICD6Features(normal)  # (icd6, keywords dict)

        # file = open(self.icd6_keywords_file, "w+")
        # file.write(",".join(keywords_set))
        # file.close()

        file = open(self.keywords_set_file, "w+")
        for (icd6, keywords) in icd6_keywords.iteritems():
            key_str = [k + ":" + str(v) for (k, v) in keywords.items()]
            file.write(icd6 + "-" + ",".join(key_str) + "\n")
        file.close()

if __name__ == "__main__":
    kw = ICD_Keywords()
    kw.writeInFile_Dict()