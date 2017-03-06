#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Preprocess import *

reload(sys)
sys.setdefaultencoding('utf8')

conn = MySQLdb.connect("localhost", "root", "10081008", "Medical", charset='utf8')

cursor = conn.cursor()

# cursor.execute('select 主要编码,疾病名称 from Norm6')
cursor.execute('select ICD,疾病名称 from I2025')
values = cursor.fetchall()
normal = getNormalNames(values) #(normalized_name, ICD-10)
icd4_dic = getICDTree(normal)

cursor.execute('select 类目编码,类目名称 from Norm3')
values = cursor.fetchall()
icd3_dict = {}
for row in values:
    icd3_dict[row[0]] = row[1]

cursor.execute('select ICD, 非标准名称, 标准疾病名 from LabeledData limit 10000;') #index, unormalized_name
# cursor.execute('select ICD, 非标准名称, 标准疾病名 from LabeledData where ICD=\'I21.404\';') #index, unormalized_name
values = cursor.fetchall()

enable_write_candidates = False
if enable_write_candidates:
    starttime = datetime.datetime.now()
    dir = "Experiment_LabeledData"
    if os.path.exists(dir) == False:
        os.mkdir(dir)
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

topK = 3
cnt_sim_k = 0

for row in values:
        normalized_id = row[0].strip()
        unnormalized_name = row[1].strip()
        normalized_name = row[2].strip()
        p_name = process(unnormalized_name)


        name_dict, match_type = getMappingResult(p_name, normal)
        match_type_distr[match_type - 1] += 1

        if match_type != 4: # 精确匹配和半精确匹配，加入父亲疾病节点
            name_dict = addFatherNode(p_name, name_dict, icd3_dict, normal)
        else: # 针对部位的语义匹配和模糊匹配，加入父亲和兄弟节点疾病
            name_dict = addFatherAndBrotherNodes(p_name, name_dict, icd3_dict, icd4_dic, normal)

        # name_dict is the candidate set(name : sim)
        len_candidates = len(name_dict)
        candidate_num[len_candidates/5] += 1

        if enable_write_candidates:
            if len_candidates != 0:
                    str_pair = [k + ":" + str(v) for k, v in name_dict.iteritems()]

                    if normalized_name in name_dict.keys(): # map correctly
                        cnt += 1
                        writeFile(crt_file, " ".join(p_name), ",".join(str_pair), normalized_name, normalized_id)
                    else: # map to a disease name but the name is not the labeled one.
                        other_nt += 1
                        writeFile(other_file, " ".join(p_name), ",".join(str_pair), normalized_name, normalized_id)
            else: # cannot map
                writeFile(wrong_file, " ".join(p_name), "---", normalized_name, normalized_id)

        # test the result of the basic disambiguation
        if len_candidates != 0:
            sort_name_list = sorted(name_dict.items(), key=lambda d: d[1], reverse=True)
            candidate_top_k = []

            # topK
            if len_candidates >= topK:
                if topK != 1:
                    candidate_top_k = [sort_name_list[i][0] for i in range(topK)]
                else:
                    # top 1
                    candidate_top_k.append(sort_name_list[0][0])

                    # 针对两个标准疾病名称的相似度并列第一情况(可能别名情况下，两个疾病的相似度相同)
                    if len_candidates >= 2 and sort_name_list[1][1] == sort_name_list[0][1]:
                        candidate_top_k.append(sort_name_list[1][0])
            else:
                candidate_top_k = [sort_name_list[i][0] for i in range(len_candidates)]

            if normalized_name in candidate_top_k:
                    cnt_sim_k += 1

print("Experiment: Test the basic disambiguation(top %d in the candidate includes the normalized disease name)" % topK)
print(cnt_sim_k)
print(float(cnt_sim_k) / float(len(values)))

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