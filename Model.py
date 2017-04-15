#!/usr/bin/env python
# coding=utf-8
from Preprocess import *
from top1_disambiguation import *
from util import getNormalNames, loadDict, write_List, getICDTree
import copy, datetime
import MySQLdb, os
from candidate_sim_generator import candidate_sim_generator

class Model(object):

    def __init__(self):
        self.conn = MySQLdb.connect("localhost", "root", "10081008", "medical", charset='utf8')
        self.cursor = self.conn.cursor()
        self.data = self.load_data()
        self.alias_dict = loadDict("./Dict/Alias.txt")

        self.topK = 1
        self.enable_write_candidates = True
        self.cnt = 0
        self.other_nt = 0
        self.dir = "Experiment"
        # self.dir = "Experiment_LabeledData_Seg"
        if os.path.exists(self.dir) == False:
            os.mkdir(self.dir)

        self.candidate_num = [0, 0, 0, 0, 0, 0]
        self.match_type_distr = [0, 0, 0, 0]

        if self.enable_write_candidates:
            self.starttime = datetime.datetime.now()
            self.wrong_file = open(self.dir + "/wrong_res.txt", "w")
            self.other_file = open(self.dir + "/mapping_other_res.txt", "w")
            self.crt_file = open(self.dir + "/crt_res.txt", "w")
            self.evaluation_file = open(self.dir + "/evaluation.txt", "w")

        cursor = self.cursor
        cursor.execute('select ICD,疾病名称 from I2025')
        values = cursor.fetchall()
        self.normal = getNormalNames(values)  # (normalized_name, ICD-10)
        self.icd4_dic = getICDTree(self.normal)

        cursor.execute('select 类目编码,类目名称 from Norm3')
        values = cursor.fetchall()
        self.icd3_names = {}
        for row in values:
            self.icd3_names[row[0]] = row[1]

        cursor.execute('select ICD, 非标准名称, 标准疾病名 from LabeledData limit 10000;')
        self.priorProb = getPriorProb(cursor.fetchall())  # 得到疾病的先验概率

    def load_data(self):
        cursor = self.cursor
        cursor.execute('select ICD, 非标准名称, 标准疾病名 from LabeledData limit 10000;')  # index, unormalized_name
        # cursor.execute('select ICD, 非标准名称, 标准疾病名 from LabeledData where ICD=\'I21.203111 \';') #index, unormalized_name
        values = cursor.fetchall()
        return values

    def begin(self):

        file = open(self.dir + "/disambiguate_res.txt", "w")
        discorrect_file = open(self.dir + "/dis_correct.txt", "w")
        cnt_sim_k = 0
        generator = candidate_sim_generator()

        for row in self.data:
            normalized_id = row[0].strip()
            unnormalized_name = row[1].strip()
            normalized_name = row[2].strip()
            p_name = process(unnormalized_name)

            isSingle, name_dict_seg = generator.getCandidates(p_name)
            top_candidate = getTopCandidate(name_dict_seg)

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

            if self.enable_write_candidates:
                self.write_cases(normalized_name, name_dict, sort_name_list, p_name, normalized_id)

            candidate_top_k = basicDisambiguation_top1(top_candidate, self.priorProb, self.icd3_names, self.normal)
            str_pair = [k + ":" + str(v) for (k, v) in sort_name_list]
            if normalized_name == candidate_top_k or \
                    (candidate_top_k in self.alias_dict.keys() and normalized_name == self.alias_dict[candidate_top_k]):
                # 标准疾病名称 = top1 或者top1的alias就认为正确
                cnt_sim_k += 1
                write_List(discorrect_file,  [" ".join(p_name), candidate_top_k, "".join(str_pair), normalized_name, normalized_id])
            else:

                write_List(file, [" ".join(p_name), candidate_top_k, "".join(str_pair), normalized_name, normalized_id])

        file.close()
        print("Experiment: Test the basic disambiguation(top %d in the candidate includes the normalized disease name)" % self.topK)
        print(cnt_sim_k)
        print(float(cnt_sim_k) / float(len(self.data)))
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
        if self.enable_write_candidates:

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
        if self.enable_write_candidates:
            self.wrong_file.close()
            self.other_file.close()
            self.crt_file.close()
            self.evaluation_file.close()
        self.cursor.close()
        self.conn.close()

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

x = Model()
#目前---考虑一个诊断包含多个病症，对每个片段生成候选实体集和，进行消岐
x.begin()
# x.begin_version1() # 不考虑诊断包含多个病症的消歧