#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Preprocess import *

reload(sys)
sys.setdefaultencoding('utf8')

conn = MySQLdb.connect("localhost", "root", "10081008", "Medical", charset='utf8')
cursor = conn.cursor()
cursor.execute('select 主要编码,疾病名称 from Norm6')
values = cursor.fetchall()

normal = getNormalNames(values) #(normalized_name, ICD-10)
normal_index_name = dict((v,k) for k,v in normal.items())

starttime = datetime.datetime.now()

cursor.execute('select S0501, S050100 from d2014_2015 limit 10000;') #index, unormalized_name
values = cursor.fetchall()

dir = "Experiment2"
if os.path.exists(dir) == False:
    os.mkdir(dir)
unmapped_file = open(dir + "/unmapped_res.txt", "w")
mapped_file = open(dir + "/mapped_res.txt", "w")
evaluation_file = open(dir + "/evaluation.txt", "w")

mapping = 0
unmapped = 0

for row in values:
        possible_normalized_id = row[0].strip()
        unnormalized_name = row[1].strip()
        possible_normalized_name = normal_index_name.get(possible_normalized_id, "")

        p_name = process(unnormalized_name)
        name_set = getMappingResult(p_name, normal)

        if len(name_set) != 0:
            mapping += 1
            writeFile(mapped_file, " ".join(p_name), ",".join(list(name_set)), possible_normalized_name, possible_normalized_id)
        else: # cannot map
            unmapped += 1
            writeFile(unmapped_file, " ".join(p_name), "---", possible_normalized_name, possible_normalized_id)

unmapped_file.close()
mapped_file.close()
endtime = datetime.datetime.now()

evaluation_file.write('标准疾病名称个数为 %d\n' % len(normal))
evaluation_file.write('可以映射到实体名称的记录个数为 %d\n' % mapping)
evaluation_file.write('不可以映射到实体名称的记录个数为 %d\n' %unmapped)
evaluation_file.write('非标准疾病名称个数为 %d\n' %  len(values))
accuracy = float(mapping) / float(len(values))
evaluation_file.write('正确分类的比例为 %f\n' % accuracy)
evaluation_file.write('运行时间' + str(endtime - starttime) + "\n")
evaluation_file.close()

cursor.close()
conn.close()