# -*- coding: UTF-8 -*-
# 在本文件中定义了一些操控配置和数据文件的工具
__author__ = 'FinalTheory'

from ConfigParser import ConfigParser
from GlobalDefs import *
import sqlite3
import socket
import sys
import web

web.config.debug = False
import os
from threading import Lock


# 首先是一些辅助函数的定义：

def check_path(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_sorted_file_list(dir_path):
    size = 0
    nums = 0
    all_info = []
    for root, dirs, files in os.walk(dir_path):
        for name in files:
            file_name = os.path.join(root, name)
            file_size = os.path.getsize(file_name)
            file_mtime = os.path.getmtime(file_name)
            size += file_size
            nums += 1
            all_info.append((file_name, file_size, file_mtime))
    return size, nums, sorted(all_info, key=lambda x: x[2])


def ip_check(ip):
    q = ip.split('.')
    return len(q) == 4 and len(filter(lambda x: 0 <= x <= 255,
                                      map(int, filter(lambda x: x.isdigit(), q)))) == 4


def check_port(port, ip='127.0.0.1', timeout=0.1):
    try:
        port = int(port)
        # 确保传入的ip地址是合法的，否则进行域名查询
        if not ip_check(ip):
            ip, port = socket.getaddrinfo(ip, port)[0][4]
        sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sk.settimeout(timeout)
        sk.connect((ip, port))
        sk.close()
        return True
    except Exception:
        return False


def check_connect():
    address = cfg.read('check_server_ip')
    port = int(cfg.read('check_server_port'))
    time_out = float(cfg.read('check_server_time_out'))
    if check_port(port, address, time_out):
        return True
    return False


# 下面是数据库处理类和配置文件处理类

class DataBaseManager():
    def __init__(self):
        # Try to open database file, if failed then create a new one
        try:
            open(cfg.read('db_filename'), 'r').close()
        except:
            self.InitDataBase()
            sys.stderr.write('Warning: database not found, created a new one!\n')
        self.mutex = Lock()

    # Method to create a entire new database
    def InitDataBase(self):
        open(cfg.read('db_filename'), 'w').close()
        with open(cfg.read('sql_filename')) as fid, \
                sqlite3.connect(cfg.read('db_filename')) as conn:
            conn.text_factory = str
            for sql in fid.read().split('\n\n'):
                if len(sql) > 3:
                    conn.execute(sql)
                    conn.commit()

    def Execute(self, sql):
        self.mutex.acquire()
        # connect to the database
        with sqlite3.connect(cfg.read('db_filename')) as conn:
            conn.text_factory = str
            conn.execute(sql)
            conn.commit()
        self.mutex.release()

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
        try:
            open(cfg_name, 'r').close()
        except:
            sys.stderr.write(u'严重错误，无法读取配置文件！程序自动退出。\n')
            sys.exit(-1)
        self.config = ConfigParser()
        self.config.read(cfg_name)
        self.system = dict(self.config.items('system'))
        self.config_check()

    def config_check(self):
        try:
            # 首先检查设定的全局存储目录是否合法
            check_path(self.read('global_pos'))
            # 然后检查管理员的下载目录是否存在
            root_path = os.path.join(self.read('global_pos'), 'root')
            if not os.path.exists(root_path):
                os.mkdir(root_path)
        except Exception, err:
            sys.stderr.write(u'系统错误，原因：%s\n' % err)
            sys.exit(-1)
        # 接下来检查端口是否可用
        if check_port(self.read('port_name')):
            sys.stderr.write(u'系统错误，端口被占用！\n')
            sys.exit(-1)

    def read(self, key):
        result = self.system.get(key)
        if type(result) == str:
            result = result.decode('gb18030')
        return result

    def write(self, key, value):
        if type(value) == unicode:
            value = value.encode('gb18030')
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
            if type(msg) == unicode:
                msg = msg.encode('gb18030')
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
