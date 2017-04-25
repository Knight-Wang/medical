#!/usr/bin/env python
# coding=utf-8
import codecs
from Preprocess import *
from top1_disambiguation import *
from util import getNormalNames, loadDict, write_List, getICDTree, getICD_file
import copy, datetime, sys, csv
import os
from candidate_sim_generator import candidate_sim_generator

class Model(object):

    def __init__(self, data, dir, dict_file, labeled):

        self.data = data
        self.labeled = labeled
        self.alias_dict = loadDict("./Dict/Alias.txt")

        self.topK = 1
        self.enable_write_candidates = True
        self.cnt = 0
        self.other_nt = 0
        self.dir = dir
        self.candidate_num = [0, 0, 0, 0, 0, 0]
        self.match_type_distr = [0, 0, 0, 0]

        if os.path.exists(self.dir) == False:
            os.mkdir(self.dir)

        if self.enable_write_candidates and self.labeled:
            self.starttime = datetime.datetime.now()
            self.wrong_file = open(self.dir + "/wrong_res.txt", "w")
            self.other_file = open(self.dir + "/mapping_other_res.txt", "w")
            self.crt_file = open(self.dir + "/crt_res.txt", "w")
            self.evaluation_file = open(self.dir + "/evaluation.txt", "w")
            self.dis_incorrect_file = open(self.dir + "/disambiguate_res.txt", "w")
            self.dis_correct_file = open(self.dir + "/dis_correct.txt", "w")

        values = getICD_file(dict_file, "\t")
        self.normal = getNormalNames(values)  # (normalized_name, ICD-10)
        self.icd4_dic = getICDTree(self.normal)
        res_file = open(dir + "result.csv", "w+")
        res_file.write(codecs.BOM_UTF8)
        self.dis_file = csv.writer(res_file) # the output file to generate the disambiguation result

        icd3_file = open("./Dict/Norm3.csv")
        line = icd3_file.readline()
        self.icd3_names = {}
        while line != "":
            row = line.strip().split("\t")
            self.icd3_names[row[0]] = row[1]
            line = icd3_file.readline()

        # conn = MySQLdb.connect("localhost", "root", "10081008", "medical", charset='utf8')
        # cursor = conn.cursor()
        # cursor.execute('select ICD, 非标准名称, 标准疾病名 from LabeledData limit 10000;')
        # values = cursor.fetchall()
        # self.priorProb = getPriorProb(values)  # 得到疾病的先验概率

        file = open("./Dict/icd6_seg.txt")
        line = file.readline().strip()
        self.tfidf_dict = {}  # (name, key words of names)

        while line != "":
            x = line.split(":")
            self.tfidf_dict[x[2]] = x[1].split(" ")
            line = file.readline().strip()

    def begin(self):

        cnt_sim_k = 0
        generator = candidate_sim_generator(self.normal, self.icd3_names)

        for row in self.data:
            normalized_id = row[0].strip()
            unnormalized_name = row[1].strip()
            if self.labeled == True:
                normalized_name = row[2].strip()
            p_name = process(unnormalized_name)

            isSingle, name_dict_seg = generator.getCandidates(p_name)
            top_candidate = getTopCandidate(name_dict_seg, p_name, self.tfidf_dict)

            # 把字典展平，一个诊断的(n+1)个候选实体集和 =》 一个候选实体集和
            name_dict = {}
            for d in name_dict_seg:
                for (k, v) in d.items():
                    if k in name_dict.keys():
                        name_dict[k] = max(name_dict[k], v)
                    else:
                        name_dict.update(d)

            # # Add Brother Node
            # if match_type == 4:
            #     name_dict = addBrotherNodes(p_name, name_dict, icd4_dic, normal, icd6_keywords)

            # candidate_num[len_candidates / 5] += 1

            sort_name_list = sorted(name_dict.items(), key=lambda d: d[1], reverse=True)[:10]
            seg_num = len(top_candidate)
            str_pair = [k + ":" + str(v) for (k, v) in sort_name_list]

            for i in range(seg_num):
                seg_top1 = top_candidate[i]
                if seg_top1 in self.alias_dict.keys():
                    top_candidate[i] = seg_top1 + "/" + self.alias_dict[seg_top1]
            self.dis_file.writerow([" ".join(p_name), " ".join(top_candidate), " ".join(str_pair)])

            if self.labeled == True:
                if self.enable_write_candidates:
                    self.write_cases(normalized_name, name_dict, sort_name_list, p_name, normalized_id)

                # candidate_top_k = basicDisambiguation_top1(top_candidate, self.priorProb, self.icd3_names, self.normal)
                candidate_top_k = top_candidate

                match = False
                for i in range(len(candidate_top_k)):
                    seg_top1 = candidate_top_k[i]
                    x = re.findall(normalized_name, seg_top1)
                    if len(x) != 0:
                            cnt_sim_k += 1
                            match = True
                            break

                if match == False:
                    write_List(self.dis_incorrect_file,
                           [" ".join(p_name), " ".join(candidate_top_k), ",".join(str_pair), normalized_name, normalized_id])
                else:
                    write_List(self.dis_correct_file, [" ".join(p_name), " ".join(candidate_top_k), "".join(str_pair), normalized_name,normalized_id])

        if self.labeled == True:
            print("Experiment: Test the basic disambiguation(top %d in the candidate includes the normalized disease name)" % self.topK)
            print(cnt_sim_k)
            print(float(cnt_sim_k) / float(len(self.data)))
            if self.enable_write_candidates:
                self.evaluate()

    def write_cases(self, normalized_name, name_dict, sort_name_list, p_name, normalized_id):
            len_candidates = len(name_dict)
            if len_candidates != 0:
                str_pair = [k + ":" + str(v) for (k, v) in sort_name_list]

                if normalized_name in name_dict.keys():  # map correctly
                    self.cnt += 1
                    write_List(self.crt_file, [" ".join(p_name), ",".join(str_pair), normalized_name, normalized_id])
                else:
                    # map to a disease name but the name is not the labeled one.
                    self.other_nt += 1
                    write_List(self.other_file, [" ".join(p_name), ",".join(str_pair), normalized_name, normalized_id])
            else:  # cannot map
                write_List(self.wrong_file, [" ".join(p_name), "---", normalized_name, normalized_id])

    def evaluate(self):
            endtime = datetime.datetime.now()
            evaluation_file = self.evaluation_file
            evaluation_file.write('标准疾病名称个数为 %d\n' % len(self.normal))
            evaluation_file.write('正确分类的记录个数为 %d\n' % self.cnt)
            evaluation_file.write('能映射，但是分类到其他疾病名称的记录个数为 %d\n' % self.other_nt)
            evaluation_file.write('非标准疾病名称个数为 %d\n' % len(self.data))
            accuracy = float(self.cnt) / float(len(self.data))
            evaluation_file.write('正确分类的比例为 %f\n' % accuracy)
            evaluation_file.write('运行时间' + str(endtime - self.starttime) + "\n")
            # evaluation_file.write('候选实体的数目分布：5位增量' + str(candidate_num) + "\n")
            # evaluation_file.write('匹配的分类分布：精确匹配，半精确匹配，部位的语义匹配，模糊匹配' + str(match_type_distr) + "\n")
            evaluation_file.close()

    def __del__(self):
        if self.enable_write_candidates and self.labeled :
            self.wrong_file.close()
            self.other_file.close()
            self.crt_file.close()
            self.evaluation_file.close()
            self.dis_incorrect_file.close()
            self.dis_correct_file.close()

    # 不考虑诊断包含多个病的情况
    def begin_version1(self):
        file = open(self.dir + "/disambiguate_res_version1.txt", "w")
        cnt_sim_k = 0

        for row in self.data:
            normalized_id = row[0].strip()
            unnormalized_name = row[1].strip()
            normalized_name = row[2].strip()
            p_name = process(unnormalized_name)

            icd6_keywords = {}
            name_dict, match_type = getMappingResult(p_name, self.normal, icd6_keywords)  # generate candidates

            self.match_type_distr[match_type - 1] += 1

            # Add Brother Node
            if match_type == 4:
                name_dict = addBrotherNodes(p_name, name_dict, self.icd4_dic, self.normal)

            # Add Alias
            dict_copy = copy.deepcopy(name_dict)
            for (k, v) in dict_copy.iteritems():
                if k in self.alias_dict.keys():
                    name_dict[self.alias_dict[k]] = v

            # name_dict is the candidate set(name : sim)
            len_candidates = len(name_dict)
            self.candidate_num[len_candidates / 5] += 1

            sort_name_list = sorted(name_dict.items(), key=lambda d: d[1], reverse=True)

            if self.enable_write_candidates:
                self.write_cases(normalized_name, name_dict, sort_name_list, p_name, normalized_id)

            # test the result of the basic disambiguation
            if len_candidates != 0:

                candidate_top_k = []

                # topK
                if len_candidates >= self.topK:
                    if self.topK != 1:
                        candidate_top_k = [sort_name_list[i][0] for i in range(self.topK)]
                    else:
                        # top 1
                        tie_tops = getTieTops(sort_name_list)  # top1 相似度并列的候选实体集
                        if (len(tie_tops) > 1):
                            tie_tops = optimizeTopCandidates(tie_tops, self.icd3_names, self.normal)
                        candidate_top_k.append(tie_tops[0][0])

                        if tie_tops[0][0] in self.alias_dict.keys():  # 别名情况下，两个疾病的相似度相同
                            candidate_top_k.append(self.alias_dict[tie_tops[0][0]])
                else:
                    candidate_top_k = [sort_name_list[i][0] for i in range(len_candidates)]

                if normalized_name in candidate_top_k:
                    cnt_sim_k += 1
                else:
                    str_pair = [k + ":" + str(v) for (k, v) in sort_name_list]
                    write_List(file, [" ".join(p_name), ",".join(str_pair), normalized_name, normalized_id])
        print(
        "Experiment: Test the basic disambiguation(top %d in the candidate includes the normalized disease name)" % self.topK)
        print(cnt_sim_k)
        print(float(cnt_sim_k) / float(len(self.data)))

for argument in sys.argv:
    print argument

file = sys.argv[1] # 待消歧文件位置
output_dir = sys.argv[2] # 消歧结果放置的文件夹
dict_file = sys.argv[3] # 标准疾病字典的位置
labeled = True if sys.argv[4] == '1' else False # 数据是否有标注

data = []
file_ = open(file)
line = file_.readline().strip()

while line != "":
    line = str(line).decode("GB2312")
    data.append(line.split(","))
    line = file_.readline().strip()

x = Model(data, output_dir, dict_file, labeled)
#目前---考虑一个诊断包含多个病症，对每个片段生成候选实体集和，进行消岐
x.begin()
# x.begin_version1() # 不考虑诊断包含多个病症的消歧