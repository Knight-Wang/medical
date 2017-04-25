#!/usr/bin/env python
# -*- coding: utf-8 -*-


def verdict(x, y):
    if x == y:
        return True
    elif (x == u'不稳定性心绞痛' and y == u'增强型心绞痛') or \
         (x == u'增强型心绞痛' and y == u'不稳定性心绞痛'):
            return True
    elif (x == u'冠状动脉痉挛' and y == u'变异型心绞痛') or \
         (x == u'变异型心绞痛' and y == u'冠状动脉痉挛'):
            return True
    return False


def test_init(name_dict):
    disease_dict = {}
    loop = 0
    for line in open("../data/i2025.txt", "r"):
        loop += 1
        if loop == 1:
            continue
        data = line.rstrip("\n").decode("UTF-8").split("\t")
        disease_dict[data[1]] = data[0]

    WRONG_FILE = "../res/bad_case_init.txt"
    RIGHT_FILE = "../res/good_case_init.txt"
    wrong_file = open(WRONG_FILE, "w")
    right_file = open(RIGHT_FILE, "w")
    cnt_all, correct, wrong = 0, 0, 0
    for i, record in enumerate(open("../data/test.txt", "r")):
        x = record.rstrip("\n").decode("UTF-8").split("\t")
        for t in x:
            d = t.split("##")
            # print d[0] + " | " + d[1]
            if d[1] == "NONE":
                continue
            cnt_all += 1
            if verdict(name_dict[d[0]][0][0], d[1]):
                correct += 1
                right_file.writelines(d[0] + " | " + name_dict[d[0]][0][0] + " | " + str(name_dict[d[0]][0][1]) + " | " + d[1] + "\n")
            else:
                wrong += 1
                wrong_file.writelines(d[0] + " | " + name_dict[d[0]][0][0] + " | " + str(name_dict[d[0]][0][1]) + " | " + d[1] + "\n")

    print "all %d" % cnt_all
    print "Correct %d" % correct
    print "Wrong %d" % wrong
    print "Percent %.3f" % (correct * 1.0 / (correct + wrong))
    wrong_file.close()
    right_file.close()


def test(res, init_res, num):
    disease_dict = {}
    loop = 0
    for line in open("../data/i2025.txt", "r"):
        loop += 1
        if loop == 1:
            continue
        data = line.rstrip("\n").decode("UTF-8").split("\t")
        disease_dict[data[1]] = data[0]

    WRONG_FILE = "../res/bad_case" + str(num) + ".txt"
    RIGHT_FILE = "../res/good_case" + str(num) + ".txt"
    wrong_file = open(WRONG_FILE, "w")
    right_file = open(RIGHT_FILE, "w")
    correct, wrong, not_in, not_in_correct, not_in_wrong = 0, 0, 0, 0, 0
    for i, record in enumerate(open("../data/test.txt", "r")):
        x = record.rstrip("\n").decode("UTF-8").split("\t")
        for t in x:
            d = t.split("##")
            # print d[0] + " | " + d[1]
            if d[1] == "NONE":
                continue
            if d[0] not in res:
                not_in += 1
                if init_res[d[0]] == d[1]:
                    correct += 1
                    not_in_correct += 1
                else:
                    wrong += 1
                    not_in_wrong += 1
                continue
            if verdict(res[d[0]][0], d[1]):
                correct += 1
                right_file.writelines(d[0] + " | " + res[d[0]][0] + " | " + str(res[d[0]][1]) + " | " + d[1] + "\n")
            else:
                wrong += 1
                wrong_file.writelines(d[0] + " | " + res[d[0]][0] + " | " + str(res[d[0]][1]) + " | " + d[1] + "\n")

    print "Correct %d" % correct
    print "Wrong %d" % wrong
    print "Not_in %d" % not_in
    print "Not_in_correct %d" % not_in_correct
    print "Not_in_wrong %d" % not_in_wrong
    print "Percent %.3f" % (correct * 1.0 / (correct + wrong))
    wrong_file.close()
    right_file.close()
