#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Preprocess import *
from top1_disambiguation import *
import MySQLdb
from copy import copy
import datetime, os
from util import *

reload(sys)
sys.setdefaultencoding('utf8')

conn = MySQLdb.connect("localhost", "root", "10081008", "medical", charset='utf8')
cursor = conn.cursor()

cursor.execute('select ICD,疾病名称 from I2025')
values = cursor.fetchall()
normal = getNormalNames(values) #(normalized_name, ICD-10)
icd4_dic = getICDTree(normal)

cursor.execute('select 类目编码,类目名称 from Norm3')
values = cursor.fetchall()
icd3_names = {}
for row in values:
    icd3_names[row[0]] = row[1]

starttime = datetime.datetime.now()

cursor.execute('select ICD, 非标准名称, 标准疾病名 from LabeledData limit 10000;')
priorProb = getPriorProb(cursor.fetchall()) # 得到疾病的先验概率
cursor.execute('select ICD, 非标准名称, 标准疾病名 from LabeledData limit 10000;') #index, unormalized_name
# cursor.execute('select ICD, 非标准名称, 标准疾病名 from LabeledData where ICD=\'I21.902001 \';') #debug

values = cursor.fetchall()

enable_write_candidates = True #是否将消歧结果写入文件
dir = "Experiment_LabeledData_Seg"
if os.path.exists(dir) == False:
    os.mkdir(dir)

if enable_write_candidates:
    starttime = datetime.datetime.now()
    wrong_file = open(dir + "/wrong_res.txt", "w")
    other_file = open(dir + "/mapping_other_res.txt", "w")
    unmap_ICD = open(dir + "/unmapped_ICD.txt", "w")
    crt_file = open(dir + "/crt_res.txt", "w")
    evaluation_file = open(dir + "/evaluation.txt", "w")

cnt = 0
other_nt = 0
unmap_id = 0
candidate_num = [0,0,0,0,0,0]
match_type_distr = [0,0,0,0]

topK = 1
cnt_sim_k = 0

file = open(dir + "/disambiguate_res.txt", "w")
alias_dict = loadDict("./Dict/Alias.txt")

file_top = open( dir + "/top_seg.txt", "w+")

for row in values:
        normalized_id = row[0].strip()
        unnormalized_name = row[1].strip()
        normalized_name = row[2].strip()
        p_name = process(unnormalized_name)

        name_dict_seg = getMappingResult_segs(p_name, normal)  # generate candidates
        top_candidate = getTopCandidate(name_dict_seg)

        name_dict = {}
        for d in name_dict_seg:
            for (k, v) in d.items():
                if k in name_dict.keys():
                    name_dict[k] = max(name_dict[k], v)
                else:
                    name_dict.update(d)
        # match_type_distr[match_type - 1] += 1
        #
        # # Add Brother Node
        # if match_type == 4:
        #     name_dict = addBrotherNodes(p_name, name_dict, icd4_dic, normal, icd6_keywords)

        # Add Alias
        dict_copy = copy(name_dict)
        for (k, v) in dict_copy.iteritems():
            if k in alias_dict.keys():
                name_dict[alias_dict[k]] = v

        # name_dict is the candidate set(name : sim)
        len_candidates = len(name_dict)
        # candidate_num[len_candidates / 5] += 1

        sort_name_list = sorted(name_dict.items(), key=lambda d: d[1], reverse=True)[:10]

        if enable_write_candidates:
            if len_candidates != 0:
                    str_pair = [k + ":" + str(v) for (k, v) in sort_name_list]

                    if normalized_name in name_dict.keys(): # map correctly
                        cnt += 1
                        write_List(crt_file, [" ".join(p_name), ",".join(str_pair), normalized_name, normalized_id])
                    else:
                    # map to a disease name but the name is not the labeled one.
                        other_nt += 1
                        write_List(other_file, [" ".join(p_name), ",".join(str_pair), normalized_name, normalized_id])
            else: # cannot map
                write_List(wrong_file, [" ".join(p_name), "---", normalized_name, normalized_id])

        candidate_top_k = basicDisambiguation_top1(top_candidate, priorProb, icd3_names, normal)
        if normalized_name == candidate_top_k or \
                (candidate_top_k in alias_dict.keys() and normalized_name == alias_dict[candidate_top_k]):
            # 标准疾病名称 = top1 或者top1的alias就认为正确
            cnt_sim_k += 1
        else:
            str_pair = [k + ":" + str(v) for (k, v) in sort_name_list]
            file.write("|".join([ " ".join(p_name),candidate_top_k, "".join(str_pair), normalized_name, normalized_id ]))

print("Experiment: Test the basic disambiguation(top %d in the candidate includes the normalized disease name)" % topK)
print(cnt_sim_k)
print(float(cnt_sim_k) / float(len(values)))

file.close()

if enable_write_candidates:
    wrong_file.close()
    other_file.close()
    crt_file.close()
    endtime = datetime.datetime.now()

    evaluation_file.write('标准疾病名称个数为 %d\n' % len(normal))
    evaluation_file.write('正确分类的记录个数为 %d\n' % cnt)
    evaluation_file.write('能映射，但是分类到其他疾病名称的记录个数为 %d\n' % other_nt)
    evaluation_file.write('非标准疾病名称个数为 %d\n' %  len(values))
    accuracy = float(cnt) / float(len(values))
    evaluation_file.write('正确分类的比例为 %f\n' % accuracy)
    evaluation_file.write('运行时间' + str(endtime - starttime) + "\n")
    evaluation_file.write('候选实体的数目分布：5位增量'+str(candidate_num) + "\n")
    evaluation_file.write('匹配的分类分布：精确匹配，半精确匹配，部位的语义匹配，模糊匹配'+str(match_type_distr) + "\n")
    evaluation_file.close()

cursor.close()
conn.close()