# -*- coding: UTF-8 -*-
# 在本文件中定义了一些操控配置和数据文件的工具
__author__ = 'FinalTheory'

from tkMessageBox import showerror
from ConfigParser import ConfigParser
import Tkinter as tk
from GlobalDefs import *
import sqlite3
import sys
import web
from threading import Lock
# web.config.debug = False


class DataBaseManager():

    def __init__(self):
        # Try to open database file, if failed then create a new one
        try:
            open(cfg.read('db_filename'), 'r').close()
        except:
            self.InitDataBase()
            sys.stderr.write('Warning: database not found, created a new one!\n')

    # Method to create a entire new database
    def InitDataBase(self):
        open(cfg.read('db_filename'), 'w').close()
        with open(cfg.read('sql_filename')) as fid,\
            sqlite3.connect(cfg.read('db_filename')) as conn:
            conn.text_factory = str
            for sql in fid.read().split('\n\n'):
                if len(sql) > 3:
                    conn.execute(sql)
                    conn.commit()

    def Execute(self, sql):
        # connect to the database
        with sqlite3.connect(cfg.read('db_filename')) as conn:
            conn.text_factory = str
            conn.execute(sql)
            conn.commit()

    def Query(self, sql):
        with sqlite3.connect(cfg.read('db_filename')) as conn:
            conn.text_factory = str
            cursor = conn.execute(sql)
            return cursor.fetchall()

    def QueryFirst(self, sql):
        with sqlite3.connect(cfg.read('db_filename')) as conn:
            conn.text_factory = str
            cursor = conn.execute(sql)
            return cursor.fetchone()


class ConfigLoader():
    def __init__(self):
        root = tk.Tk()
        root.withdraw()
        try:
            open(cfg_name, 'r').close()
        except:
            showerror(u'严重错误', u'无法读取配置文件！程序自动退出。')
            exit(-1)
        self.config = ConfigParser()
        self.config.read(cfg_name)
        self.system = dict(self.config.items('system'))

    def read(self, key):
        return self.system.get(key)

    def write(self, key, value):
        self.system[key] = value
        self.config.set('system', key, value)
        self.config.write(open(cfg_name, "w"))


class LogManager:
    def __init__(self):
        open(cfg.read('log_filename'), 'w').close()
        self.mutex = Lock()

    def log_message(self, msg):
        self.mutex.acquire()
        with open(cfg.read('log_filename'), 'a') as fid:
            # 自动加上换行
            if msg[-1] != '\n':
                msg += '\n'
            fid.write(msg)
        self.mutex.release()


# In debug mode, web.py will load global variable twice,
# so we have to use this trick to avoid this.
if web.config.get('_db') is None:
    cfg = ConfigLoader()
    log = LogManager()
    db = DataBaseManager()
    web.config._cfg = cfg
    web.config._log = log
    web.config._db = db
else:
    cfg = web.config._cfg
    log = web.config._log
    db = web.config._db