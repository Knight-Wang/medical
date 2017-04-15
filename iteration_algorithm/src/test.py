#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: sunmeng(sunmeng94@163.com)
"""
from conf import *
import processor

def alias_mapping(name):
    if name == u"变异型心绞痛":
        return u"冠状动脉痉挛"
    elif name == u"增强型心绞痛":
        return u"不稳定性心绞痛"
    else:
        return name

class Tester():
    def __init__(self):
        self.records = []
        self.groundtruth = []
        for line in open(TEST_FILE, "r"):
            data = line.rstrip("\n").decode("UTF-8").split("\t")
            record = {
                "main": [],
                "other": []
            }
            groundtruth = {
                "main": [],
                "other": []
            }
            for i, string in enumerate(data):
                mention, entity = string.split("##")
                if i == 0:
                    key = "main"
                else:
                    key = "other"
                record[key].append(mention)
                groundtruth[key].append(entity)
            self.records.append(record)
            self.groundtruth.append(groundtruth)
    
    def test(self, processor, suffix="nosuffix"):
        correct, wrong = 0, 0
        badcases = {}
        with open("../res/test.log.%s" % suffix, "w") as f_out:
            for i, record in enumerate(self.records):
                print >> f_out, "------------------ Record %d ----------------------" % i
                res = processor.disambiguate(record)
                mentions = []
                for key in record:
                    for j, mention in enumerate(record[key]):
                        top1_list = []
                        output_list = [mention, self.groundtruth[i][key][j]]
                        for item in res[key][j]:
                            output_list.append("##".join([item[0], str(item[1])]))
                            mentions.append(item[0])
                            if item[1] == res[key][j][0][1]:
                                top1_list.append(item[0])
                        output_list.append(str(len(top1_list)))
                        print >> f_out, "\t".join(output_list).encode("UTF-8")
                        if self.groundtruth[i][key][j] != "NONE":
                            if alias_mapping(self.groundtruth[i][key][j]) in map(alias_mapping, top1_list):
                                correct += 1
                            else:
                                wrong += 1
                                badcase = (top1_list[0], self.groundtruth[i][key][j])
                                if badcase in badcases:
                                    badcases[badcase] += 1
                                else:
                                    badcases[badcase] = 1
                                print >> f_out, "WRONG_FLAG"
                if processor.network is not None:
                    for i, m1 in enumerate(mentions):
                        for j, m2 in enumerate(mentions):
                            if i != j:
                                print >> f_out, ("%s\t%s\t%.8f" % (m1, m2, processor.network.edge(m1, m2))).encode("UTF-8")
                    for m in mentions:
                        print >> f_out, ("%s\t%.8f" % (m, processor.network.popSim(m))).encode("UTF-8")
            print >> f_out, "Correct: %d\nWrong: %d\n" % (correct, wrong)
        print "Correct: %d\nWrong: %d\nPercent: %.6f" % (correct, wrong, float(correct) / (correct + wrong))
        #for badcase in badcases:
        #    print badcase[0], badcase[1], badcases[badcase]

if __name__ == "__main__":
    tester = Tester()
    tester.test(processor.processor)
