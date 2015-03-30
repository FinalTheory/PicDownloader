# -*- coding: UTF-8 -*-

__author__ = 'FinalTheory'

import json
import sha
import web
web.config.debug = False
import os
import sys
from re import match
from random import random
from mako.template import Template
from time import time
from Tools import cfg, db, check_path
from shutil import rmtree
from GlobalDefs import *


# 页面映射
urls = (
    # 主页
    '/', 'Root',
    '/index', 'Index',
    # 注册及登录
    '/login', 'Login',
    '/logout', 'Logout',
    '/register', 'Register',
    # 管理URL规则
    '/modify_rules', 'ModifyRules',
    # 管理当前任务
    '/modify_tasks', 'ModifyTasks',
    # 用户设置
    '/settings', 'Settings',
    # 管理员功能
    '/admin', 'Admin',
    # 日志显示功能
    '/log', 'Log',
)

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
        if UserStatus == USER_STATUS_ADMIN or UserStatus == USER_STATUS_NORMAL:
            return True, UserInfo
        elif UserStatus == USER_STATUS_FORBIDDEN:
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
            SessionID = sha.new(repr(time()) + str(random())).hexdigest()
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
        # 首先检查UID是否合法
        if not UID.isalnum():
            return Notice(u'注册失败', u'用户ID必须由字母和数字构成！', '/register')
        # 其次检查UID是否重复
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
            # TODO: 更改数据库格式，去除无用设置
            sql = "INSERT INTO `Users`(`UID`,`SessionID`,`UserStatus`," \
                  "`UserName`,`PassWord`,`Tel`,`E-mail`,`MaxSize`,`MaxFiles`,`Downloader`) " \
                  "VALUES ('%s',NULL,1,'%s','%s','%s','%s',%d,%d,'%s');" \
                  % (UID, UserName, PassWord, Tel, E_mail, MaxSize, MaxFiles, cfg.read('downloader'))
            # 尝试为用户创建家目录
            user_path = os.path.join(cfg.read('global_pos'), UID)
            if not os.path.exists(user_path):
                os.mkdir(user_path)
            # 如果家目录创建成功，才更新数据库
            db.Execute(sql)
            return Notice(u'注册成功', u'请使用你新注册的帐号登录系统。', '/login')
        except Exception, err:
            return Notice(u'注册失败', u'错误: %s 请检查你的注册信息是否合法有效！' % err, '/register')


class ModifyRules():
    def GET(self):
        stat, UserInfo = CheckLogin()
        if stat:
            if UserInfo['UserStatus'] == USER_STATUS_FORBIDDEN:
                return Notice(u'无效访问',  u'被封禁用户无权操作！', '/login')
            MyTemplate = CreateMyTemplate('ModifyRules.html')
            if UserInfo['UserStatus'] == USER_STATUS_ADMIN:
                sql = "SELECT Rule_Name, URL_Rule, Status, RepeatType, RepeatValue, TaskID, TimeZone " \
                      "FROM UserTask"
            else:
                sql = "SELECT Rule_Name, URL_Rule, Status, RepeatType, RepeatValue, TaskID, TimeZone " \
                      "FROM UserTask WHERE UID='%s'" % UserInfo['UID']
            results = db.Query(sql)
            return MyTemplate.render(results=results)
        else:
            return Notice(u'无效访问',  u'请先登录！', '/login')

    def POST(self):
        stat, UserInfo = CheckLogin()
        if stat:
            if UserInfo['UserStatus'] == USER_STATUS_FORBIDDEN:
                return json.dumps({
                    'status': 401,
                    'msg': u'被封禁用户无权操作！'
                })
            UID = UserInfo['UID'].encode('utf-8')
            data = web.input(month=[], day=[], hour=[], minute=[])
            action = data.get('action', '')
            URL_Rule = data.get('URL_Rule', '').encode('utf-8')
            # 检查URL是否合法
            if match('^\w+://', URL_Rule) is None:
                URL_Rule = 'http://%s' % URL_Rule
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
                    # 注意要删除任务对应文件夹：
                    sql = "SELECT `UID`, `SubDirectory` FROM `UserTask` WHERE `TaskID` = %d" % TaskID
                    Dirs = db.QueryFirst(sql)
                    del_path = os.path.join(cfg.read('global_pos'),
                                            Dirs[0].decode('utf-8'),
                                            Dirs[1].decode('utf-8'))
                    if Dirs[1] and os.path.exists(del_path):
                        rmtree(del_path)
                    sql = "DELETE FROM `UserTask` WHERE `TaskID`=%d" % TaskID
                    db.Execute(sql)
                    sql = "DELETE FROM `CurrentTask` WHERE `TaskID`=%d" % TaskID
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
                        'day': REP_PER_DAY,
                        'week': int(data['Weekday']),
                        'month': REP_PER_MONTH,
                        'year': REP_PER_YEAR,
                        'once': REP_PER_ONCE
                    }
                    idx = dic2idx[RepeatType]
                    RepeatLevel = dic2val[RepeatType]
                    RepeatValue = ' '.join(map(str, map(int, [lst_year[idx], lst_month[idx],
                                                              lst_day[idx], lst_hour[idx], lst_minute[idx]])))
                    SubDir = data.get('Sub_Dir', '')
                    NameRule = data.get('NameRule', 'auto').encode('utf-8')
                    Downloader = data.get('Downloader', 'aria2').encode('utf-8')
                    CheckType = data.get('CheckType', 'auto').encode('utf-8')
                    TaskTime = int(data.get('TaskTime', '12'))
                    CheckSize = int(data.get('CheckSize', '4096'))
                    sql = "INSERT INTO UserTask (UID, URL_Rule, Rule_Name, RepeatType, RepeatValue, " \
                          "TimeZone, Status, SubDirectory, NameRule, TaskTime, Downloader, CheckType, CheckSize) " \
                          "VALUES ('%s', '%s', '%s', %d, '%s', '%s', %d, '%s', '%s', %d, '%s', '%s', %d)" % \
                          (UID, URL_Rule, Rule_Name, RepeatLevel, RepeatValue, TimeZone, Status,
                           SubDir.encode('utf-8'), NameRule, TaskTime, Downloader, CheckType, CheckSize)
                    if len(URL_Rule) == 0 or len(Rule_Name) == 0:
                        raise Exception(u'请输入有效的下载链接和任务名称')
                    # 为任务建立子目录
                    # 注意路径必须是unicode编码的！
                    Rule_Folder = os.path.join(cfg.read('global_pos'), UID, SubDir)
                    if not os.path.exists(Rule_Folder):
                        os.mkdir(Rule_Folder)
                    db.Execute(sql)
                    return json.dumps({
                        'status': 200,
                        'msg': u'操作成功！'
                    })
                except Exception, err:
                    return json.dumps({
                        'status': 400,
                        'msg': u'意外错误：%s。请检查你的输入数据。' % err
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
        if stat and UserInfo['UserStatus'] == USER_STATUS_ADMIN:
            MyTemplate = CreateMyTemplate('Admin.html')

            sql = "SELECT UID, UserName, PassWord, MaxFiles, MaxSize FROM Users"
            AllUserData = db.Query(sql)
            return MyTemplate.render(
                AllUserData=AllUserData,
                SiteName=cfg.read('site_name'),
                GlobalPos=cfg.read('global_pos'),
                DateCheckingInterval=cfg.read('date_checking_interval'),
                WorkerCheckingInterval=cfg.read('worker_checking_interval'),
                CleanerCheckingInterval=cfg.read('cleaner_checking_interval'),
                PortName=cfg.read('port_name'),
                MaxThreads=cfg.read('max_threads'),
                MaxBuf=cfg.read('max_buf'),
            )
        else:
            return Notice(u'禁止访问',  u'非管理员无权操作！', '/index')

    def POST(self):
        stat, UserInfo = CheckLogin()
        if stat and UserInfo['UserStatus'] == USER_STATUS_ADMIN:
            data = web.input()
            action = data.get('action')
            # TODO: 增加一个停止/启动所有线程的功能
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
                    sql = "DELETE FROM `Users` WHERE `UID`='%s'" % UID
                    db.Execute(sql)
                    sql = "DELETE FROM `UserTask` WHERE `UID`='%s'" % UID
                    db.Execute(sql)
                    sql = "DELETE FROM `CurrentTask` WHERE `UID`='%s'" % UID
                    db.Execute(sql)
                    # 最后注意删除用户的目录
                    del_path = os.path.join(cfg.read('global_pos'), UID)
                    if os.path.exists(del_path):
                        rmtree(del_path)
                    return json.dumps({
                        'status': 200,
                        'msg': u'操作成功！'
                    })
                except Exception, err:
                    return json.dumps({
                        'status': 400,
                        'msg': u'%s\n请检查学号/工号是否合法！' % err
                    })
            elif action == 'config':
                # TODO: 增加几个新设置项的处理机制
                try:
                    # TODO: 这里可以为更多设置项增加检查函数，似乎这就是单子的一种用法吧？
                    CheckFunc = {
                        'SiteName': None,
                        'GlobalPos': check_path,
                        'DateCheckingInterval': int,
                        'WorkerCheckingInterval': int,
                        'CleanerCheckingInterval': int,
                        'PortName': int,
                        'MaxThreads': int,
                        'MaxBuf': int
                    }
                    ConfigName2Str = {
                        'SiteName': 'site_name',
                        'GlobalPos': 'global_pos',
                        'DateCheckingInterval': 'date_checking_interval',
                        'WorkerCheckingInterval': 'worker_checking_interval',
                        'CleanerCheckingInterval': 'cleaner_checking_interval',
                        'PortName': 'port_name',
                        'MaxThreads': 'max_threads',
                        'MaxBuf': 'max_buf'
                    }
                    # 首先检查一遍全部数据，看其中是否有空项
                    for key in ConfigName2Str.keys():
                        val = data.get(key)
                        if not val:
                            raise Exception(u'提交的数据中存在无效项/空项！')
                        if CheckFunc[key]:
                            CheckFunc[key](val)
                    # 如果所有数据正常，就直接继续更新
                    for key in ConfigName2Str.keys():
                        val = data.get(key)
                        cfg.write(ConfigName2Str[key], val)
                    return json.dumps({
                        'status': 200,
                        'msg': u'操作成功！'
                    })
                except Exception, err:
                    return json.dumps({
                        'status': 400,
                        'msg': u'%s\n请检查输入数据是否合法！' % err
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


class ModifyTasks():
    def GET(self):
        stat, UserInfo = CheckLogin()
        if stat:
            if UserInfo['UserStatus'] == USER_STATUS_FORBIDDEN:
                return Notice(u'无效访问',  u'被封禁用户无权操作！', '/login')
            MyTemplate = CreateMyTemplate('ModifyTasks.html')
            if UserInfo['UserStatus'] == USER_STATUS_ADMIN:
                sql = "SELECT * FROM `CurrentTask`"
            else:
                sql = "SELECT * FROM `CurrentTask` WHERE `UID` = '%s'" % UserInfo['UID']
            results = db.Query(sql)
            return MyTemplate.render(CurrentTask=results)
        else:
            return Notice(u'无效访问',  u'请先登录！', '/login')

    def POST(self):
        pass


class Log():
    def GET(self):
        stat, UserInfo = CheckLogin()
        if stat:
            if UserInfo['UserStatus'] != USER_STATUS_ADMIN:
                return Notice(u'无效访问',  u'普通用户无权操作！', '/login')
            return open(cfg.read('log_filename'), 'r').read().encode('utf-8')
        else:
            return Notice(u'无效访问',  u'请先登录！', '/login')


def start_web_server():
    app = web.application(urls, globals())
    sys.stderr.write('Web server started at %d port!\n' % int(cfg.read('port_name')))
    # 启动http服务监听指定端口
    web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", int(cfg.read('port_name'))))

