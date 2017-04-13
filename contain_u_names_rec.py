#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import DataBase
reload(sys)
sys.setdefaultencoding('utf8')


def init():
    """ 初始化
    :return: 标准疾病名称字典,
             标准手术名称字典,
             医疗记录,
             标注数据
    """
    d = DataBase.DataBase()
    values = d.query('select ICD, 疾病名称 from I2025')

    normal_diseases = {}  # 标准疾病名称字典 <key, value> = <名称, 编码>
    for v in values:
        normal_diseases[v[1]] = v[0]

    print '标准疾病名称个数为 %d' % len(normal_diseases)

    values = d.query('select ICD, 手术名称 from heart_surgery')
    normal_surgeries = {}  # 标准手术名称字典 <key, value> = <名称, 编码>
    for v in values:
        normal_surgeries[v[1]] = v[0]

    print '标准手术名称个数为 %d' % len(normal_surgeries)

    medical_records_2013 = d.query('select  S050100, S050200, S050600, S050700, \
                                            S050800, S050900, S051000, S051100, \
                                            S056000, S056100, S056200, \
                                            S050501, S051201, S051301, S051401, \
                                            S051501, S057001, S057101, S057201, \
                                            S057301, S057401 \
                                       from heart_new_2013')

    # medical_records_2014_15 = d.query('select  S050100, S050200, S050600, S050700, \
    #                                            S050800, S050900, S051000, S051100, \
    #                                            S056000, S056100, S056200, \
    #                                            S050501, S051201, S051301, S051401, \
    #                                            S051501, S057001, S057101, S057201, \
    #                                            S057301, S057401 \
    #                                       from heart_new limit 100000')

    # medical_records_2013[len(medical_records_2013):len(medical_records_2013)] = medical_records_2014_15

    print '医疗记录为 %d 条' % len(medical_records_2013)

    values = d.query('select 非标准名称, 标准疾病名 from LabeledData_3')
    labeled_data = {}
    for s in values:
        labeled_data[s[0].strip()] = s[1].strip()

    print '测试数据个数为 %d' % len(labeled_data)

    return normal_diseases, normal_surgeries, medical_records_2013, labeled_data


def get_graph(normal_diseases, normal_surgeries, medical_records, labeled_data):
    """ 构建伴病网络
    :param normal_diseases: 标准疾病名称集合
    :param normal_surgeries: 标准手术名称集合
    :param medical_records: 医疗记录
    :return: G -> 构建好的伴病网络，使用 networkx 实现
             not_single -> 至少有一个邻居的 疾病 或 手术 名称（非孤立点）集合
    """

    cnt_u_in = 0  # 在非标准疾病名称字典中的非标准疾病名称数量
    cnt_u_not_in = 0  # 不在非标准疾病名称字典中的非标准疾病名称数量
    cnt_n = 0  # 标准疾病名称的数量
    cnt_all = 0  # 医疗记录的数量
    cnt_n_s = 0  # 标准手术名称
    res = {}
    for t in medical_records:
        cnt_all += 1
        if not (cnt_all % 100000):
            print cnt_all
        now = 0
        for s in t:
            s = s.strip()
            now += 1
            if not s:
                continue
            if s == 'NA':
                continue
            if now <= 11:  # 这是个疾病名称
                if s in normal_diseases.keys():
                    cnt_n += 1
                elif s in labeled_data.keys():
                    cnt_u_in += 1
                    if s not in res:
                        res[s] = 1
                    else:
                        res[s] += 1
                else:
                    cnt_u_not_in += 1
            else:
                if s in normal_surgeries.keys():
                    cnt_n_s += 1

    print '记录总数 %d' % cnt_all
    print '合法名称总数 %d' % (cnt_n + cnt_u_in + cnt_u_not_in)
    print '标准疾病名称数量 %d' % cnt_n
    print '在字典中的非标准疾病名称 %d' % cnt_u_in
    print '不在字典中的非标准疾病名称 %d' % cnt_u_not_in
    print '标准手术名称 %d' % cnt_n_s
    for k, v in res.iteritems():
        print k, v

normal_dis, normal_sur, records, labeled_data = init()
get_graph(normal_dis, normal_sur, records, labeled_data)


