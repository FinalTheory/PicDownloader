# -*- coding: UTF-8 -*-
__author__ = 'FinalTheory'

import os
import sys
import unittest
import BeautifulSoup as bs
from pytz import timezone
import requests
from .. Tools import cfg, db
from .. WebServer import start_web_server
from .. DownloadServer import DownloadServer
from thread import start_new_thread
from datetime import datetime
from shutil import copyfile, rmtree
from tempfile import mkdtemp
from time import sleep


# TODO: 增加完善的单元测试
# 主要测试的内容：
# 1. 修改个人信息等功能，以及其异常处理
# 2. 用户管理、系统全局设置等
# 3. 下载任务的更新、处理等，重点测试对时区的支持
# 4. 线程池的并发性测试，满载模拟


data_modify_rule = {
    # 操作类型
    'action': 'add',
    # 规则名称
    'Rule_Name': '',
    # 子目录位置
    'Sub_Dir': '',
    # 下载链接
    'URL_Rule': 'https://www.baidu.com/img/bdlogo.png',
    # 下面这几个是指定日期
    # 注意支持用List的写法
    # 并且生成的POST数据会按照List中元素的顺序
    'RepeatType': '',
    'Weekday': '1',
    'year': '',
    'month': ['', ''],
    'day': ['', '', ''],
    'hour': ['', '', '', '', ''],
    'minute': ['', '', '', '', ''],
    # 任务状态
    'Status': '1',
    # 时区
    'TimeZone': '',
    # 其他一些设置
    'NameRule': 'auto',
    'Downloader': 'aria2',
    'TaskTime': '12',
    'CheckType': 'auto',
    'CheckSize': '4096'
}

data_user_add = {
    'UID': '',
    'PassWord': '12345678',
    'UserName': '',
    'Tel': '15689100026',
    'E-mail': '123@qq.com',
    'MaxFiles': '1234',
    'MaxSize': '1234'
}

temp_dir = ''

class BasicTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BasicTest, self).__init__(*args, **kwargs)

    # 类初始化和清理函数
    @classmethod
    def setUpClass(cls):
        db_file = cfg.read('db_filename')
        db_file = os.path.join(os.getcwd(), db_file)
        cfg_file = os.path.join(os.getcwd(), 'config.ini')
        # 首先备份现有的数据库
        if os.path.exists(db_file):
            os.rename(db_file, db_file + '.bak')
        # 备份现有的配置文件
        if os.path.exists(cfg_file):
            copyfile(cfg_file, cfg_file + '.bak')
        # 然后生成一个新的数据库
        db.InitDataBase()
        # 生成临时文件夹
        global temp_dir
        temp_dir = mkdtemp(prefix='PicDownloader_')
        cfg.write('global_pos', temp_dir)
        cfg.config_check()
        # 最后启动HTTP服务
        start_new_thread(start_web_server, ())

    @classmethod
    def tearDownClass(cls):
        db_file = cfg.read('db_filename')
        db_file = os.path.join(os.getcwd(), db_file)
        cfg_file = os.path.join(os.getcwd(), 'config.ini')
        # 删除用于测试的数据库文件
        if os.path.exists(db_file):
            os.remove(db_file)
        # 删除测试用的配置文件
        if os.path.exists(cfg_file):
            os.remove(cfg_file)
        # 删除临时文件夹
        global temp_dir
        if temp_dir and os.path.exists(temp_dir):
            rmtree(temp_dir)
        # 然后恢复原本的文件
        if os.path.exists(db_file + '.bak'):
            os.rename(db_file + '.bak', db_file)
        if os.path.exists(cfg_file + '.bak'):
            os.rename(cfg_file + '.bak', cfg_file)

class TestWebFunction(BasicTest):
# ********************************下面是辅助的函数等********************************

    def __init__(self, *args, **kwargs):
        super(TestWebFunction, self).__init__(*args, **kwargs)

    # 返回登录后的session以及信息
    def login(self, UID, password, expires=31536000):
        s = requests.Session()
        post_url = 'http://localhost/login'
        post_data = {
            'UID': UID,
            'password': password,
            'expires': expires
        }
        r = s.post(post_url, data=post_data)
        return s, r

    def login_root(self):
        return self.login('root', '3.1415926')

# ********************************下面是正式测试用例********************************

    def test_00_init(self):
        self.assertTrue(True)

    def test_01_login_logout(self):
        # 首先建立一个登录后的会话
        # 测试登录
        s, r = self.login_root()
        self.assertTrue('/admin' in r.text)
        self.assertTrue('/log' in r.text)
        self.assertTrue('/modify_tasks' in r.text)
        self.assertTrue('/modify_rules' in r.text)
        self.assertTrue(u'查看任务' in r.text)
        self.assertTrue(u'管理规则' in r.text)
        # 测试登出
        r = s.get('http://localhost/logout')
        self.assertTrue('/login' in r.text)
        self.assertTrue('password' in r.text)
        self.assertTrue(u'注册' in r.text)
        self.assertTrue(u'登录' in r.text)

    def test_02_add_user(self):
        s, r = self.login_root()
        post_url = 'http://localhost/register'
        post_data = data_user_add
        post_data['UID'] = 'test01'
        post_data['UserName'] = u'黄'
        r = s.post(post_url, data=post_data)
        self.assertTrue(u'注册成功' in r.text)
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test01')))
        # 测试能否检查到重复
        r = s.post(post_url, data=post_data)
        self.assertTrue(u'重复的' in r.text)
        # 测试能否检测到非法参数
        post_data['MaxFiles'] = ''
        post_data['UID'] = 'test02'
        r = s.post(post_url, data=post_data)
        self.assertTrue(u'合法有效' in r.text)
        self.assertFalse(os.path.exists(os.path.join(temp_dir, 'test02')))
        # 测试能否检测到非法UID
        post_data['UID'] = u'test02草泥马'
        r = s.post(post_url, data=post_data)
        self.assertTrue(u'字母和数字' in r.text)
        self.assertFalse(os.path.exists(os.path.join(temp_dir, 'test02')))
        # 最后注册一个合法的ID
        post_data['MaxFiles'] = '1024'
        post_data['UID'] = 'test02'
        post_data['UserName'] = u'侯颖琳'
        r = s.post(post_url, data=post_data)
        self.assertTrue(u'注册成功' in r.text)
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test02')))

    def test_03_add_rule_01(self):
        s, r = self.login_root()
        post_url = 'http://localhost/modify_rules'
        post_data = data_modify_rule
        # 保证这个任务处于有效时间段内
        tz = 'UTC'
        test_name = u'测试01'
        now = datetime.now(timezone(tz))
        post_data['hour'][0] = str(now.hour)
        post_data['minute'][0] = str(now.minute)
        post_data['Rule_Name'] = test_name
        post_data['Sub_Dir'] = test_name
        post_data['RepeatType'] = 'day'
        post_data['TimeZone'] = tz
        r = s.post(post_url, data=post_data)
        # 检查操作是否成功
        self.assertTrue('200' in r.text)
        # 检查是否生成了对应的目录
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'root', test_name)))

    def test_03_add_rule_02(self):
        s, r = self.login('test01', '12345678')
        # 确认正确登录
        self.assertTrue(u'管理规则' in r.text)
        post_url = 'http://localhost/modify_rules'
        post_data = data_modify_rule
        # 增加一个周任务
        # 保证这个任务处于有效时间段内
        tz = 'Asia/Shanghai'
        test_name = u'测试02'
        now = datetime.now(timezone(tz))
        post_data['RepeatType'] = 'week'
        post_data['Weekday'] = now.isoweekday()
        post_data['hour'][1] = str(now.hour)
        post_data['minute'][1] = str(now.minute)
        post_data['Rule_Name'] = test_name
        post_data['Sub_Dir'] = test_name
        post_data['TimeZone'] = tz
        r = s.post(post_url, data=post_data)
        # 检查操作是否成功
        self.assertTrue('200' in r.text)
        # 检查是否生成了对应的目录
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test01', test_name)))

    def test_03_add_rule_03(self):
        s, r = self.login('test02', '12345678')
        # 确认正确登录
        self.assertTrue(u'管理规则' in r.text)
        post_url = 'http://localhost/modify_rules'
        post_data = data_modify_rule
        # 增加一个月任务
        tz = 'Asia/Shanghai'
        test_name = u'测试03'
        now = datetime.now(timezone(tz))
        post_data['RepeatType'] = 'month'
        post_data['day'][0] = str(now.day)
        post_data['hour'][2] = str(now.hour)
        post_data['minute'][2] = str(now.minute)
        post_data['Rule_Name'] = test_name
        post_data['Sub_Dir'] = test_name
        post_data['TimeZone'] = tz
        r = s.post(post_url, data=post_data)
        # 检查操作是否成功
        print r.text
        self.assertTrue('200' in r.text)
        # 检查是否生成了对应的目录
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test02', test_name)))

    def test_03_add_rule_04(self):
        s, r = self.login('test01', '12345678')
        # 确认正确登录
        self.assertTrue(u'管理规则' in r.text)
        post_url = 'http://localhost/modify_rules'
        post_data = data_modify_rule
        # 增加一个年任务
        tz = 'Asia/Shanghai'
        test_name = u'测试04哈哈哈'
        now = datetime.now(timezone(tz))
        post_data['RepeatType'] = 'year'
        post_data['month'][0] = str(now.month)
        post_data['day'][1] = str(now.day)
        post_data['hour'][3] = str(now.hour)
        post_data['minute'][3] = str(now.minute)
        post_data['Rule_Name'] = test_name
        post_data['Sub_Dir'] = test_name
        post_data['TimeZone'] = tz
        r = s.post(post_url, data=post_data)
        # 检查操作是否成功
        print r.text
        self.assertTrue('200' in r.text)
        # 检查是否生成了对应的目录
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test01', test_name)))

    def test_03_add_rule_05(self):
        s, r = self.login('test02', '12345678')
        # 确认正确登录
        self.assertTrue(u'管理规则' in r.text)
        post_url = 'http://localhost/modify_rules'
        post_data = data_modify_rule
        # 增加一个单次任务
        tz = 'America/New_York'
        test_name = u'测试05哈哈哈哈'
        now = datetime.now(timezone(tz))
        post_data['RepeatType'] = 'once'
        post_data['year'] = str(now.year)
        post_data['month'][1] = str(now.month)
        post_data['day'][2] = str(now.day)
        post_data['hour'][4] = str(now.hour)
        post_data['minute'][4] = str(now.minute)
        post_data['Rule_Name'] = test_name
        post_data['Sub_Dir'] = test_name
        post_data['TimeZone'] = tz
        r = s.post(post_url, data=post_data)
        # 检查操作是否成功
        print r.text
        self.assertTrue('200' in r.text)
        # 检查是否生成了对应的目录
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test02', test_name)))

    def test_04_check_db(self):
        # 检查数据库，此时应该有5个用户任务和?个用户
        sql = "SELECT COUNT(`TaskID`) FROM `UserTask`"
        num = db.Query(sql)
        self.assertTrue(num[0][0] == 5)
        sql = "SELECT COUNT(`UID`) FROM `Users`"
        num = db.Query(sql)
        self.assertTrue(num[0][0] == 3)

    def test_05_check_threads_func(self):
        # 这个测试是检查线程功能是否正确
        num_tasks = 5
        # 创建一个下载服务器
        server = DownloadServer(True)
        # 首先更新当前任务
        server.update_calendar()
        # 检查当前任务表中是否出现了足够的任务
        sql = "SELECT COUNT(`TaskID`) FROM `CurrentTask`"
        self.assertTrue(db.Query(sql)[0][0] == num_tasks)
        # 然后将任务加载到缓冲区，检查是否出现了正确的任务
        server.update_worker()
        self.assertTrue(len(server.thread_pool.working_queue) == num_tasks)
        # 接下来启动线程池
        server.thread_pool.start()
        # 检查任务缓冲区中的元素是否被移除
        sleep(0.2)
        self.assertTrue(len(server.thread_pool.working_queue) == 0)
        # 检查线程池中是否启动了正确数量的线程
        sleep(0.2)
        self.assertTrue(server.thread_pool.count_working_thread() == num_tasks)
        # 还要等待所有线程结束才行，不然数据库有锁
        sleep(3)

    def test_99_modify_del_user(self):
        pass

    def test_add_tasks(self):
        pass

    def test_query_tasks(self):
        pass

    def test_system_admin(self):
        pass

if __name__ == '__main__':
    unittest.main()