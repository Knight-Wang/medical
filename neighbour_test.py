#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import DataBase as db
from Preprocess import *
import copy

reload(sys)
sys.setdefaultencoding('utf8')


def load_normal_name_dict():
    """ 载入别名字典
    :return: 别名字典 <key, value> = <别名, 标准名称>
    """
    f = open("./Dict/Alias.txt", "r")
    res = {}
    try:
        while True:
            line = f.readline().strip()
            if not line:
                break
            names = line.split(" ")
            normal = names[0].decode("utf-8")
            for e in names:
                res[e.decode("utf-8")] = normal
    finally:
        f.close()
    return res


def get_network(records, disease, surgeries):
    """ 构建伴病网络
    :param records: 医疗记录
    :param disease: 标准疾病名称集合
    :param surgeries: 标准手术名称集合
    :return: 伴病网络字典 <key, value> = <标准疾病名称, set(标准疾病名称1, 标准疾病名称2, ...)>
             非标准疾病名称的伴病(邻居)字典 <key, value> = <非标准疾病名称, set(标准名称1, 标准名称2, ...)>
    """
    G = {}  # 伴病网络 邻接表
    bad_names = {}  # 存储非标准疾病名称和它的标准疾病名称邻居们
    appear = {}  # 单个标准疾病名称出现次数
    co_appear = {}  # <标准疾病名称1, 标准疾病名称2> 出现次数
    alias_dict = load_normal_name_dict()  # 别名字典，把别名都映射成一个确定的标准疾病名称
    cnt_row = 0
    for t in records:
        cnt_row += 1
        if cnt_row % 100000 == 0:
            print "第 %d 行" % cnt_row
        link = set()  # 这条记录中的标准名称集合
        bad = set()  # 这条记录中的非标准名称集合
        now = 0
        for s in t:
            now += 1
            if not s:
                continue
            if now < 11:  # 疾病名称
                # segs = process(s)
                # name_dict, type = getMappingResult(segs, disease)
                # if name_dict:
                    # res = dic2list(name_dict)
                    # if res[0][1] > 0.857:  # 可信度比较高，直接认为是标准疾病名称
                if s in disease:#
                    # 在这里解决别名问题
                    n = copy.copy(s)
                    if s in alias_dict:
                        n = alias_dict[s]
                    link.add(n)
                    if n not in appear:
                        appear[n] = 1
                    appear[n] += 1
                else:  # 未匹配
                    bad.add(s)
            else:  # 手术名称
                if s in surgeries:
                    link.add(s)
                    if s not in appear:
                        appear[s] = 1
                    appear[s] += 1
        for b in bad:  # 给“坏”名字添加“好”邻居
            if b not in bad_names:
                bad_names[b] = set()
            for l in link:
                bad_names[b].add(l)
        for x in link:
            for y in link:
                if x < y:
                    tmp = (x, y)
                    if tmp not in co_appear:
                        co_appear[tmp] = 1
                    co_appear[tmp] += 1

    for (x, y) in co_appear:
        if x not in G:
            G[x] = set()
        G[x].add(y)
        if y not in G:
            G[y] = set()
        G[y].add(x)

    f = codecs.open("texts/out/graph.txt", "w", "utf-8")
    try:
        f.writelines(str(len(G.keys())) + '\n')
        for x in G:
            tmp = x
            if not len(G[x]):
                continue
            f.writelines(tmp + ' ' + str(len(G[x])) + '\n')
            for y in G[x]:
                f.writelines(y)
                a = min(x, y)
                b = max(x, y)
                val = co_appear[(a, b)] * 1.0 / appear[x]
                f.writelines(' ' + str(val) + '\n')
    finally:
        f.close()

    f = open("texts/out/bad_names.txt", "w")
    try:
        for b in bad_names:
            f.writelines(b + "    ")
            for n in bad_names[b]:
                f.writelines(n + " ")
            f.writelines("\n")
    finally:
        f.close()
    return G, bad_names


def init():
    """ 初始化
    :return: normal_disease 标准疾病名称(6位编码)集合,
             normal_surgeries 标准手术名称集合,
             medical_records 医疗记录集合
    """
    d = db.DataBase()
    values = d.query('select ICD, 疾病名称 from I2025')
    normal_disease = getNormalNames(values)

    values = d.query('select 手术名称 from heart_surgery')
    normal_surgeries = set()  # 标准手术名称集合
    for t in values:
        for s in t:
            normal_surgeries.add(s)

    medical_records = d.query('select S050100, S050200, S050600, S050700, \
                                  S050800, S050900, S051000, S051100, \
                                  S056000, S056100, S056200, \
                                  S050501, S051201, S051301, S051401, \
                                  S051501, S057001, S057101, S057201, \
                                  S057301, S057401 \
                             from heart_new')

    return normal_disease, normal_surgeries, medical_records


if __name__ == "__main__":

    normal_disease, normal_surgeries, medical_records = init()
    start_time = datetime.datetime.now()
    print "开始构建伴病网络"
    G, bad_names = get_network(medical_records, normal_disease, normal_surgeries)
    end_time = datetime.datetime.now()
    print "构建伴病网络时间为 %d秒" % (end_time - start_time).seconds
    cnt_node = len(G)
    cnt_edge = 0
    for x in G:
        cnt_edge += len(G[x])
    print "节点数：%d" % cnt_node
    print "边数：%d" % cnt_edge
