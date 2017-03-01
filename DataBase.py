#!/usr/bin/env python
# coding=utf-8

import mysql.connector


class DataBase(object):
    def __init__(self):
        self.conn = mysql.connector.connect(user='root',
                                            password='123456',
                                            database='medical',
                                            use_unicode='True')
        self.cursor = self.conn.cursor(buffered=True)

    def query(self, sql):
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def __del__(self):
        self.cursor.close()
        self.conn.close()
