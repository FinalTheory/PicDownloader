# -*- coding: UTF-8 -*-

__author__ = 'FinalTheory'

import web
import json
# web.config.debug = False
import sys
import sha
import time
import sqlite3
import threading
import subprocess
from random import random
from ConfigParser import ConfigParser
from tkMessageBox import showerror
from mako.template import Template
from tempfile import gettempdir, TemporaryFile
import Tkinter as tk

cfg_name = 'config.ini'


class GlobalDef():
    USER_STATUS_ADMIN = 0
    USER_STATUS_NORMAL = 1
    USER_STATUS_FORBIDDEN = 2
    USER_STATUS_NOT_LOGGED = -1

# 页面映射
urls = (
    # 主页
    '/', 'Root',
    '/index', 'Index',
    # 注册及登录
    '/login', 'Login',
    '/logout', 'Logout',
    '/register', 'Register',
    # 管理任务规则
    '/modify_rules', 'ModifyRules',
    # 管理当前下载任务
    '/modify_tasks', 'ModifyTasks',
    # 用户设置
    '/settings', 'Settings',
    # 管理员功能
    '/admin', 'Admin',
)


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
        return self.system[key]

    def write(self, key, value):
        self.system[key] = value
        self.config.set('system', key, value)
        self.config.write(open(cfg_name, "w"))


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


# In debug mode, web.py will load global variable twice,
# so we have to use this trick to avoid this.
if web.config.get('_db') is None:
    cfg = ConfigLoader()
    db = DataBaseManager()
    web.config._cfg = cfg
    web.config._db = db
else:
    cfg = web.config._cfg
    db = web.config._db


def CreateMyTemplate(filename):
        return Template(
            filename='static/' + filename,
            input_encoding='utf-8',
            output_encoding="utf-8",
            encoding_errors='replace'
        )


def Notice(title, msg, url):
    MyTemplate = CreateMyTemplate('Notice.html')
    return MyTemplate.render(title=title, msg=msg, url=url)


def CheckLogin():
    SessionID = web.cookies().get('SessionID', None)
    result = db.QueryFirst('SELECT UID, UserStatus, UserName, Tel, '
                           '`E-mail`, MaxSize, MaxFiles FROM Users WHERE SessionID="%s"' % SessionID)
    if result:
        UserInfo = {
            'UID': result[0].decode('utf-8'),
            'UserStatus': result[1],
            'UserName': result[2].decode('utf-8'),
            'Tel': result[3].decode('utf-8'),
            'E-mail': result[4].decode('utf-8'),
            'MaxSize': result[5],
            'MaxFiles': result[6]
        }
        UserStatus = result[1]
        if UserStatus == GlobalDef.USER_STATUS_ADMIN or UserStatus == GlobalDef.USER_STATUS_NORMAL:
            return True, UserInfo
        elif UserStatus == GlobalDef.USER_STATUS_FORBIDDEN:
            return True, UserInfo
        else:
            return False, {}
    else:
        return False, {}


class Root():
    def GET(self):
        web.seeother('/index')


class Index():
    def GET(self):
        stat, UserInfo = CheckLogin()
        if stat:
            MyTemplate = CreateMyTemplate('Index.html')
            return MyTemplate.render(SiteName=cfg.read('site_name'), **UserInfo)
        else:
            web.seeother('/login')


class Login():
    def GET(self):
        MyTemplate = CreateMyTemplate('Login.html')
        return MyTemplate.render()

    def POST(self):
        data = web.input()
        UID = data.get('UID')
        PassWd = data.get("password")
        expire = data.get('expires')
        sql = 'SELECT UserName, UserStatus FROM Users WHERE UID = "%s" AND PassWord = "%s"' \
              % (UID, PassWd)
        result = db.QueryFirst(sql)
        if result:
            SessionID = sha.new(repr(time.time()) + str(random())).hexdigest()
            web.setcookie('SessionID', SessionID, int(expire))
            sql = 'UPDATE Users SET SessionID = "%s" WHERE UID = "%s"' % (SessionID, UID)
            db.Execute(sql)
            web.seeother('/index')
        else:
            return Notice(u'登录失败',  u'密码错误', '/login')


class Logout():
    def GET(self):
        stat, UserInfo = CheckLogin()
        if stat:
            sql = 'UPDATE Users SET SessionID = NULL WHERE UID = "%s"' % UserInfo['UID']
            db.Execute(sql)
            web.seeother('index')
        else:
            return Notice(u'访问错误',  u'当前您尚未登录，页面将自动跳转。', '/index')


class Register():

    def GET(self):
        MyTemplate = CreateMyTemplate("Register.html")
        return MyTemplate.render()

    def POST(self):
        data = web.input()
        UID = data.get('UID').encode('utf-8')
        result = db.QueryFirst("SELECT * FROM Users WHERE UID='%s'" % UID)
        if result:
            return Notice(u'注册失败', u'重复的学号/工号！', '/register')
        try:
            UserName = data.get('UserName').encode('utf-8')
            PassWord = data.get('PassWord').encode('utf-8')
            Tel = data.get('Tel').encode('utf-8')
            E_mail = data.get('E-mail').encode('utf-8')
            MaxSize = int(data.get('MaxSize'))
            MaxFiles = int(data.get('MaxFiles'))
            sql = "INSERT INTO `Users`(`UID`,`SessionID`,`UserStatus`," \
                  "`UserName`,`PassWord`,`Tel`,`E-mail`,`MaxSize`,`MaxFiles`,`Downloader`) " \
                  "VALUES ('%s',NULL,1,'%s','%s','%s','%s',%d,%d,'%s');" \
                  % (UID, UserName, PassWord, Tel, E_mail, MaxSize, MaxFiles, cfg.read('downloader'))
            db.Execute(sql)
            return Notice(u'注册成功', u'请使用你新注册的帐号登录系统。', '/login')
        except:
            return Notice(u'注册失败', u'未知错误，请检查你的注册信息是否合法有效！', '/register')


class ModifyRules():
    def GET(self):
        stat, UserInfo = CheckLogin()
        if stat:
            if UserInfo['UserStatus'] == GlobalDef.USER_STATUS_FORBIDDEN:
                return Notice(u'无效访问',  u'被封禁用户无权操作！', '/login')
            MyTemplate = CreateMyTemplate('ModifyRules.html')
            sql = "SELECT Rule_Name, URL_Rule, Status, RepeatType, RepeatValue, TaskID, TimeZone " \
                  "FROM UserTask WHERE UID='%s'" % UserInfo['UID']
            results = db.Query(sql)
            return MyTemplate.render(results=results)
        else:
            return Notice(u'无效访问',  u'请先登录！', '/login')

    def POST(self):
        stat, UserInfo = CheckLogin()
        if stat:
            if UserInfo['UserStatus'] == GlobalDef.USER_STATUS_FORBIDDEN:
                return json.dumps({
                    'status': 401,
                    'msg': u'被封禁用户无权操作！'
                })
            UID = UserInfo['UID'].encode('utf-8')
            data = web.input(month=[], day=[], hour=[], minute=[])
            action = data.get('action', '')
            URL_Rule = data.get('URL_Rule', '').encode('utf-8')
            Rule_Name = data.get('Rule_Name', '').encode('utf-8')
            Status = int(data.get('Status', '0'))
            TaskID = int(data.get('TaskID', '0'))
            if action == 'modify':
                try:
                    sql = "UPDATE UserTask SET URL_Rule='%s', Status=%d, Rule_Name='%s' "\
                          "WHERE TaskID=%d" % (URL_Rule, Status, Rule_Name, TaskID)
                    db.Execute(sql)
                    return json.dumps({
                        'status': 200,
                        'msg': u'操作成功！'
                    })
                except Exception, e:
                    return json.dumps({
                        'status': 400,
                        'msg': u'意外错误：%s。请检查你的输入数据。' % e
                    })
            elif action == 'delete':
                try:
                    sql = "DELETE FROM UserTask WHERE TaskID=%d" % TaskID
                    db.Execute(sql)
                    return json.dumps({
                        'status': 200,
                        'msg': u'操作成功！'
                    })
                except Exception, e:
                    return json.dumps({
                        'status': 400,
                        'msg': u'意外错误：%s。删除失败！' % e
                    })
            elif action == 'add':
                try:
                    RepeatType = data['RepeatType']
                    TimeZone = data['TimeZone'].encode('utf-8')
                    lst_day = ['0', data['Weekday']]
                    lst_month = ['0', '0', '0']
                    lst_year = ['0', '0', '0', '0', data.get('year')]
                    lst_day.extend(data['day'])
                    lst_month.extend(data['month'])
                    lst_minute = data['minute']
                    lst_hour = data['hour']
                    dic2idx = {
                        'day': 0,
                        'week': 1,
                        'month': 2,
                        'year': 3,
                        'once': 4
                    }
                    dic2val = {
                        'day': 0,
                        'week': int(data['Weekday']),
                        'month': 8,
                        'year': 9,
                        'once': 10
                    }
                    idx = dic2idx[RepeatType]
                    RepeatLevel = dic2val[RepeatType]
                    RepeatValue = ' '.join(map(str, map(int, [lst_year[idx], lst_month[idx],
                                                              lst_day[idx], lst_hour[idx], lst_minute[idx]])))
                    sql = "INSERT INTO UserTask (UID, URL_Rule, Rule_Name, RepeatType, RepeatValue, " \
                          "TimeZone, Status) VALUES ('%s', '%s', '%s', %d, '%s', '%s', %d)" % \
                          (UID, URL_Rule, Rule_Name, RepeatLevel, RepeatValue, TimeZone, Status)
                    if len(URL_Rule) == 0 or len(Rule_Name) == 0:
                        raise Exception(u'请输入有效的下载链接和任务名称')
                    db.Execute(sql)
                    return json.dumps({
                        'status': 200,
                        'msg': u'操作成功！'
                    })
                except Exception, e:
                    return json.dumps({
                        'status': 400,
                        'msg': u'意外错误：%s。请检查你的输入数据。' % e
                    })
            else:
                return json.dumps({
                    'status': 405,
                    'msg': u'无法识别的请求！'
                })
        else:
            return json.dumps({
                'status': 401,
                'msg': u'尚未登录，操作失败！'
            })


class Settings():
    def GET(self):
        stat, UserInfo = CheckLogin()
        if stat:
            sql = "SELECT UserName, Tel, `E-mail`, MaxFiles, MaxSize, NameRule, Downloader " \
                  "FROM Users WHERE UID='%s'" % UserInfo['UID']
            result = db.QueryFirst(sql)
            MyTemplate = CreateMyTemplate('Settings.html')
            return MyTemplate.render(SiteName=cfg.read('site_name'), UserInfo=result)
        else:
            web.seeother('/login')

    def POST(self):
        stat, UserInfo = CheckLogin()
        if stat:
            data = web.input()
            UID = UserInfo.get('UID').encode('utf-8')
            sql = "SELECT PassWord FROM Users WHERE UID='%s'" % UID
            OldPassWord = db.QueryFirst(sql)[0].encode('utf-8')
            if data.get('OldPassWord') == OldPassWord:
                try:
                    UserName = data['UserName'].encode('utf-8')
                    Tel = data['Tel'].encode('utf-8')
                    E_mail = data['E-mail'].encode('utf-8')
                    MaxFiles = int(data['MaxFiles'])
                    MaxSize = int(data['MaxSize'])
                    NameRule = data['NameRule'].encode('utf-8')
                    Downloader = data['Downloader'].encode('utf-8')
                    NewPassword = data['NewPassWord'].encode('utf-8')
                    if not NewPassword:
                        NewPassword = OldPassWord
                    sql = "UPDATE Users SET UserName='%s', Tel='%s', PassWord='%s', " \
                          "`E-mail`='%s', MaxFiles=%d, MaxSize=%d, NameRule='%s', " \
                          "Downloader='%s' WHERE UID='%s'" % (UserName, Tel, NewPassword,
                            E_mail, MaxFiles, MaxSize, NameRule, Downloader, UID)
                    db.Execute(sql)
                    return Notice(u'操作成功', u'信息修改成功，页面将自动刷新。', '/settings')
                except:
                    return Notice(u'操作失败', u'异常错误，请检查你的输入是否合法！', '/settings')
            else:
                return Notice(u'操作失败', u'密码错误！', '/settings')
        else:
            web.seeother('/login')


class Admin():
    def GET(self):
        stat, UserInfo = CheckLogin()
        if stat and UserInfo['UserStatus'] == GlobalDef.USER_STATUS_ADMIN:
            MyTemplate = CreateMyTemplate('Admin.html')

            sql = "SELECT UID, UserName, PassWord, MaxFiles, MaxSize FROM Users"
            AllUserData = db.Query(sql)
            return MyTemplate.render(
                AllUserData=AllUserData,
                Downloader=cfg.read('downloader'),
                SiteName=cfg.read('site_name'),
                GlobalPos=cfg.read('global_pos')
            )
        else:
            return Notice(u'禁止访问',  u'非管理员无权操作！', '/index')

    def POST(self):
        stat, UserInfo = CheckLogin()
        if stat and UserInfo['UserStatus'] == GlobalDef.USER_STATUS_ADMIN:
            data = web.input()
            action = data.get('action')
            if action == 'modify':
                try:
                    UID = data.get('UID').encode('utf-8')
                    UserName = data.get('UserName').encode('utf-8')
                    PassWord = data.get('PassWord').encode('utf-8')
                    MaxFiles = int(data.get('MaxFiles'))
                    MaxSize = int(data.get('MaxSize'))
                    sql = "UPDATE Users SET UserName='%s', PassWord='%s', MaxFiles=%d, MaxSize=%d " \
                          "WHERE UID='%s'" % (UserName, PassWord, MaxFiles, MaxSize, UID)
                    db.Execute(sql)
                    return json.dumps({
                        'status': 200,
                        'msg': u'操作成功！'
                    })
                except:
                    return json.dumps({
                        'status': 400,
                        'msg': u'未知错误！请检查数据是否合法！'
                    })
            elif action == 'delete':
                try:
                    UID = data.get('UID').encode('utf-8')
                    if UID == 'root':
                        raise Exception(u'不允许删除管理员！')
                    sql = "DELETE FROM Users WHERE UID='%s'" % UID
                    db.Execute(sql)
                    sql = "DELETE FROM UserTask WHERE UID='%s'" % UID
                    db.Execute(sql)
                    return json.dumps({
                        'status': 200,
                        'msg': u'操作成功！'
                    })
                except:
                    return json.dumps({
                        'status': 400,
                        'msg': u'未知错误！请检查学号/工号是否合法！'
                    })
            elif action == 'config':
                try:
                    Downloader = data.get('Downloader')
                    SiteName = data.get('SiteName')
                    GlobalPos = data.get('GlobalPos')
                    cfg.write('downloader', Downloader)
                    cfg.write('site_name', SiteName)
                    cfg.write('global_pos', GlobalPos)
                    return json.dumps({
                        'status': 200,
                        'msg': u'操作成功！'
                    })
                except:
                    return json.dumps({
                        'status': 400,
                        'msg': u'未知错误！请检查输入数据是否合法！'
                    })
            else:
                return json.dumps({
                    'status': 405,
                    'msg': u'无法识别的请求！'
                })

        else:
            return json.dumps({
                'status': 401,
                'msg': u'非管理员无权操作！'
            })

if __name__ == '__main__':
    app = web.application(urls, globals())
    web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", 80))
