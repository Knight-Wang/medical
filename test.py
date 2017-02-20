#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mysql.connector
import sys
import datetime
import re
from io import FileIO

reload(sys)
sys.setdefaultencoding('utf8')

def process (str):
    res = str.replace('&nbsp;', '')
    #res = res.replace('?', '')
    #res = res.replace('？', '')
    res = re.split('\(|\)| |\*|（|）|\[|\]|【|】|,|，|、|;|；', res)
    return [x for x in filter (lambda x : x != '', res)]

def isNormal (l, n):
    for x in l:
        if x in n:
            return True
    return False

conn = mysql.connector.connect(user = 'root',
                               password = '123456',
                               database = 'medical',
                               use_unicode = 'True')
cursor = conn.cursor(buffered = True)

cursor.execute('select 疾病名称 from norm6')

values = cursor.fetchall()
normal = set() #标准疾病名称集合

for t in values:
    for s in t:
        if isinstance(s, unicode):
            normal.add(s.decode('utf-8'))

print '标准疾病名称个数为 %d' % len(normal)

starttime = datetime.datetime.now()
cursor.execute('select S050100 from d2014_2015 limit 7000000')

values = cursor.fetchall()

f = open("res.txt", "w")
cnt = 0
for t in values:
    for s in t:
        tmp = process(s)
        if isNormal(tmp, normal):
        #if s in normal:
            cnt += 1
        #    print s.decode()
        else:
            f.writelines(s + '\n')
f.close()
endtime = datetime.datetime.now()
print '正确分类的记录个数为 %d' % cnt
print '非标准疾病名称个数为 %d' % len(values)
print '运行时间%d秒' % (endtime - starttime).seconds
cursor.close()
conn.close()
