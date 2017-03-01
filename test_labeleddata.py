#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Preprocess import *

reload(sys)
sys.setdefaultencoding('utf8')

conn = MySQLdb.connect("localhost", "root", "10081008", "Medical", charset='utf8')

cursor = conn.cursor()

cursor.execute('select 主要编码,疾病名称 from Norm6')
# cursor.execute('select ICD,疾病名称 from I2025')
values = cursor.fetchall()
normal = getNormalNames(values) #(normalized_name, ICD-10)

starttime = datetime.datetime.now()

cursor.execute('select ICD, 非标准名称, 标准疾病名 from LabeledData limit 10000;') #index, unormalized_name
values = cursor.fetchall()

dir = "Experiment_LabeledData"
if os.path.exists(dir) == False:
    os.mkdir(dir)
wrong_file = open(dir + "/wrong_res.txt", "w")
other_file = open(dir + "/mapping_other_res.txt", "w")
unmap_ICD = open(dir + "/unmapped_ICD.txt", "w")
evaluation_file = open(dir + "/evaluation.txt", "w")

cnt = 0
other_nt = 0
unmap_id = 0

for row in values:
        normalized_id = row[0].strip()
        unnormalized_name = row[1].strip()
        normalized_name = row[2].strip()
        p_name = process(unnormalized_name)

        name_dict = getMappingResult(p_name, normal)

        if len(name_dict) != 0:
                if normalized_name in name_dict.keys(): # map correctly
                    cnt += 1
                else: # map to a disease name but the name is not the labeled one.
                    other_nt += 1
                    str_pair = [k + ":" + str(v) for k,v in name_dict.iteritems()]
                    writeFile(other_file, " ".join(p_name), ",".join(str_pair), normalized_name, normalized_id)
        else: # cannot map
            writeFile(wrong_file, " ".join(p_name), "---", normalized_name, normalized_id)

wrong_file.close()
other_file.close()
endtime = datetime.datetime.now()

evaluation_file.write('标准疾病名称个数为 %d\n' % len(normal))
evaluation_file.write('正确分类的记录个数为 %d\n' % cnt)
evaluation_file.write('能映射，但是分类到其他疾病名称的记录个数为 %d\n' % other_nt)
evaluation_file.write('非标准疾病名称个数为 %d\n' %  len(values))
accuracy = float(cnt) / float(len(values))
evaluation_file.write('正确分类的比例为 %f\n' % accuracy)
evaluation_file.write('运行时间' + str(endtime - starttime) + "\n")
evaluation_file.close()

cursor.close()
conn.close()