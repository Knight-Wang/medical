#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mysql.connector
import sys
import datetime
import re
import codecs
import SimRank as SR

reload(sys)
sys.setdefaultencoding('utf8')


def process(name):
    result = name.replace('&nbsp;', '')
    result = re.split('\(|\)| |\*|（|）|\[|\]|【|】|,|，|、|;|；', result)
    return [x for x in filter(lambda x: x != '', result)]


def is_normal(l, n):
    for x in l:
        if x in n:
            return x
    return None

conn = mysql.connector.connect(user='root',
                               password='123456',
                               database='medical',
                               use_unicode='True')
cursor = conn.cursor(buffered=True)

cursor.execute('select 疾病名称 from norm6')

values = cursor.fetchall()
normal = set() #标准疾病名称集合

for t in values:
    for s in t:
        normal.add(s)

print '标准疾病名称个数为 %d' % len(normal)

start_time = datetime.datetime.now()
cursor.execute('select S050100, S050200, S050600, S050700, \
                       S050800, S050900, S051000, S051100, \
                       S056000, S056100, S056200 \
                from d2014_2015 limit 10000')

values = cursor.fetchall()

cursor.close()
conn.close()

G = {}
total = set()  # 标准疾病名称集合
total_bad = {}  # <非标准疾病名称, 出现次数>
cnt = 0
cnt_all = 0

bad_names = {}  # 存储非标准疾病名称和它的标准疾病名称邻居们

for t in values:
    link = set()  # 这条记录中的标准名称集合
    bad = set()  # 这条记录中的非标准名称集合
    for s in t:
        if s:
            tmp = process(s)
            res = is_normal(tmp, normal)
            cnt_all += 1
            if res:  # 成功匹配
                link.add(res)
                total.add(res)
                cnt += 1
            else:  # 未匹配
                bad.add(s)
                if s not in total_bad:
                    total_bad[s] = 1
                total_bad[s] += 1
    for b in bad:  # 给“坏”名字添加“好”邻居
        if b not in bad_names:
            bad_names[b] = set()
        for l in link:
            bad_names[b].add(l)
    for x in link:
        for y in link:
            if x not in G:
                G[x] = set()
            if y not in G:
                G[y] = set()
            if x != y:
                G[x].add(y)
                G[y].add(x)
end_time = datetime.datetime.now()
print '正确分类的记录个数为 %d' % cnt
print '非标准疾病名称个数为 %d' % cnt_all
print '运行时间%d秒' % (end_time - start_time).seconds
print '已经识别的种类数为 %d' % len(total)

del values

f = codecs.open("graph.txt", "w", "utf-8")
try:
    for x in G:
        tmp = x
        if len(G[x]):
            tmp += ' '
            l = len(G[x])
            i = 0
            for y in G[x]:
                tmp += y
                if i != l - 1:
                    tmp += ' '
                i += 1
        f.writelines(tmp + '\n')
finally:
    f.close()

f = codecs.open("bad_names.txt", "w", "utf-8")
try:
    for b in bad_names:
        tmp = b
        cnt = len(bad_names[b])
        if cnt:
            tmp += ' '
            i = 0
            for gn in bad_names[b]:
                tmp += gn
                if i != cnt - 1:
                    tmp += ' '
                i += 1
        f.writelines(tmp + '\n')
finally:
    f.close()

f = open("bad_guys.txt", "w")
res = sorted(total_bad.iteritems(), key=lambda d: d[1], reverse=True)
try:
    for x in res:
        tmp = ''
        tmp += x[0]
        tmp += ' '
        tmp += str(x[1])
        f.writelines(tmp + '\n')
finally:
    f.close()


if __name__ == "__main__":
    s = SR.SimRank(graph_file="graph_test.txt")
    s.sim_rank()
    print s.sim_matrix
