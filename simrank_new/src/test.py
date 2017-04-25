#!/usr/bin/env python
# -*- coding: utf-8 -*-


def test(res):
    correct, wrong, not_in = 0, 0, 0
    for i, record in enumerate(open("../data/test.txt", "r")):
        x = record.split("\t")
        print x
        # for t in x:
        #     d = t.split("##")
        #     if d[1] == "NONE":
        #         continue
        #     if d[0] not in res:
        #         not_in += 1
        #         continue
        #     if res[d] == d[1]:
        #         correct += 1
        #     else:
        #         wrong += 1
    print correct, wrong, not_in

test({})
