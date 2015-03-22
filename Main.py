# -*- coding: UTF-8 -*-

__author__ = 'FinalTheory'


import json

import os
import sha
from dateutil import parser
from random import random
from mako.template import Template
from tempfile import gettempdir, TemporaryFile
from time import time
from datetime import datetime, timedelta
from pytz import timezone
from ThreadPool import *
from GlobalDefs import *

from Tools import *

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
            if UserInfo['UserStatus'] == USER_STATUS_FORBIDDEN:
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
            if UserInfo['UserStatus'] == USER_STATUS_FORBIDDEN:
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
        if stat and UserInfo['UserStatus'] == USER_STATUS_ADMIN:
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
        if stat and UserInfo['UserStatus'] == USER_STATUS_ADMIN:
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


class MainServer():
    def __init__(self):
        self.prev_day = {}
        self.thread_pool = ThreadPool(
            int(cfg.read('max_threads')),
            int(cfg.read('max_buf')),
            cfg.read('downloader'),
            cfg.read('check_if_success'),
            int(cfg.read('size_if_success'))
        )
        # 启动所有线程
        self.thread_pool.start()

    # 这个方法对于每个任务，判断是否进入了新的一天
    # 如果是的话，就将新的任务增加到任务列表中
    def update_calendar(self, overwrite_time=None):
        sql = "SELECT * FROM `UserTask` WHERE `Status` != 0"
        all_tasks = db.Query(sql)
        for task in all_tasks:
            # 首先读取时区信息，并转换为当前任务的所在时区
            TimeZone = timezone(str(task[6]))
            if overwrite_time is None:
                today = TimeZone.localize(datetime.now())
            else:
                today = overwrite_time

            # 然后判断在该时区是否进入了新的一天
            is_new_day = False
            if self.prev_day.get(TimeZone, None) is None \
                    or today.day != self.prev_day[TimeZone]:
                self.prev_day[TimeZone] = today.day
                is_new_day = True

            # 如果确实进入了新的一天
            if is_new_day:
                # 首先生成任务开始和结束时间
                # 同样注意转换为任务所在的时区
                date_nums = map(int, task[5].split())
                StartTime = TimeZone.localize(datetime(year=today.year,
                                         month=today.month,
                                         day=today.day,
                                         hour=date_nums[3],
                                         minute=date_nums[4]))
                FinishTime = StartTime + timedelta(hours=int(cfg.read('task_time')))

                 # 生成一些与日期相关的数据
                yesterday = today + timedelta(days=-1)
                tomorrow = today + timedelta(days=1)
                keywords = {
                    '%year%': today.year,
                    '%mon%': today.month,
                    '%day%': today.day,
                    '%prev_year%': yesterday.year,
                    '%prev_mon%': yesterday.month,
                    '%prev_day%': yesterday.day,
                    '%next_year%': tomorrow.year,
                    '%next_mon%': tomorrow.month,
                    '%next_day%': tomorrow.day
                }
                for key in keywords.keys():
                        keywords[key] = '%02d' % keywords[key]

                # 其次生成下载链接
                # 用dict中的关键字不断替换URL中字符串
                TaskID = task[0]
                UID = task[1]
                URL = task[2]
                for key in keywords.keys():
                    while URL.find(key) != -1:
                        URL = URL.replace(key, keywords[key])
                # 生成URL后，更新文件保存位置
                Location = cfg.read('global_pos')
                if cfg.read('name_rule') == 'url':
                    Location = os.path.join(Location, URL.split('/')[-1])
                else:
                    Location = os.path.join(Location, task[3] + URL.split('.')[-1])

                sql = "INSERT INTO `CurrentTask` VALUES ('%s', '%s', 1, '%s', '%s', '%s', %d, '%s', 0)" % (
                        UID, URL, Location, StartTime.ctime(), FinishTime.ctime(), TaskID, TimeZone.zone)

                RepeatType = int(task[4])
                if RepeatType == REP_PER_DAY:
                    # 如果是每天执行的任务，直接添加到任务列表
                    db.Execute(sql)
                elif REP_PER_MON <= RepeatType <= REP_PER_SUN:
                    # 如果是周任务，则当前weekday必须匹配
                    if today.isoweekday() == RepeatType:
                        db.Execute(sql)
                elif RepeatType == REP_PER_MONTH:
                    # 如果是月任务，日期必须匹配
                    if today.day == date_nums[2]:
                        db.Execute(sql)
                elif RepeatType == REP_PER_YEAR:
                    # 如果是年任务，月日必须匹配
                    if today.month == date_nums[1] and today.day == date_nums[2]:
                        db.Execute(sql)
                elif RepeatType == REP_PER_ONCE:
                    # 对于仅执行一次的任务，年月日必须匹配
                    # 并且放入任务列表中后就暂停掉这项任务
                    if today.year == date_nums[0] and today.month == date_nums[1] and today.day == date_nums[2]:
                        db.Execute(sql)
                        db.Execute("UPDATE `UserTask` SET `Status` = 0 WHERE `TaskID` = %d" % TaskID)

    # 这个方法定时检查任务列表
    # 将过期的任务从任务列表中删除
    # 将未过期的任务添加到下载线程池
    # 任务被重试的次数越多，则下载优先级越低
    def update_worker(self, overwrite_time=None):
        # 首先选择所有任务列表中未暂停的任务
        sql = "SELECT * FROM `CurrentTask` WHERE `Status` != 0 ORDER BY `RepeatTimes` ASC"
        all_task = db.Query(sql)
        # 对于每一项任务进行处理，加入缓冲区
        for task in all_task:
            # 利用任务的时区信息，实例化两个时间戳
            TimeZone = timezone(task[7])
            if overwrite_time is None:
                Now = TimeZone.localize(datetime.now())
            else:
                Now = overwrite_time
            StartTime = TimeZone.localize(parser.parse(task[4]))
            FinishTime = TimeZone.localize(parser.parse(task[5]))
            TaskID = task[6]
            if Now > FinishTime:
                # 如果任务已经超时，直接删除
                sql = "DELETE FROM `CurrentTask` WHERE `TaskID` = %d" % TaskID
                db.Execute(sql)
            elif Now < StartTime:
                # 如果该任务尚未开始，就继续处理下一项任务
                continue
            else:
                # 如果这项任务应该被执行，就将其放入缓冲区
                data = {
                    'TaskID': TaskID,
                    'URL': task[1],
                    'Location': task[3]
                }
                self.thread_pool.insert(data)

    # “生产者”函数的守护线程
    def worker_daemon(self):
        while True:
            sleep(int(cfg.read('worker_checking_interval')))
            self.update_worker()

    # 维护任务列表的方法的守护线程
    def calendar_daemon(self):
        while True:
            self.update_calendar()
            sleep(int(cfg.read('date_checking_interval')))


if __name__ == '__main__':
    server = MainServer()
    app = web.application(urls, globals())
    # 首先启动日历线程更新任务列表
    start_new_thread(server.calendar_daemon, ())
    # 然后才启动生产者线程
    start_new_thread(server.worker_daemon, ())
    # 最后启动http服务监听端口
    web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", int(cfg.read('port_name'))))
