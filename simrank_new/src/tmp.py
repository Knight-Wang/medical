#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cPickle


def load():
    with open("../data/network.bin", "rb") as data_file:
        network = cPickle.load(data_file)
    with open("../data/name_dict.bin", "rb") as data_file:
        name_dic = cPickle.load(data_file)
    with open("../data/init_res.bin", "rb") as data_file:
        init_res = cPickle.load(data_file)
    return network, name_dic, init_res
network, name_dic, init_res = load()
cnt = 0
cnt_n = 0
cnt_u = 0
n_names = set()
u_names = set()
for n in network.nodes():
    if not network.neighbors(n):
        cnt += 1
        if network.node[n]["type"] == 1:
            cnt_n += 1
            n_names.add(n)
        else:
            u_names.add(n)
            cnt_u += 1
print "孤立点的个数 %d" % cnt
print "孤立点中标准名称的个数 %d" % cnt_n
print "孤立点中非标准名称的个数 %d" % cnt_u

with open("../res/normal_isolated_vertex.txt", "w") as data_file:
    for n in n_names:
        data_file.writelines(n + "\n")

with open("../res/unnormal_isolated_vertex.txt", "w") as data_file:
    for u in u_names:
        data_file.writelines(u + "\n")
