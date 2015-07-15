# -*- coding: UTF-8 -*-
__author__ = 'FinalTheory'

import sys
sys.path.append(".")
sys.path.append("..")
import os
import unittest
import BeautifulSoup as bs
from pytz import timezone
import requests
from Tools import cfg, db, check_port, check_connect
from WebServer import start_web_server
from DownloadServer import DownloadServer
from thread import start_new_thread
from datetime import datetime
from shutil import copyfile, rmtree
from tempfile import mkdtemp
from time import sleep
import imghdr

temp_file_name = 'test.txt'

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
        # 首先检查目标端口是否已经启动了一个程序
        if check_port(cfg.read('port_name')):
            sys.stderr.write('Port %s is being used! Exit!\n' % cfg.read('port_name'))
            exit(-1)
        db_file = cfg.read('db_filename')
        db_file = os.path.join(os.getcwd(), db_file)
        cfg_file = os.path.join(os.getcwd(), 'config.ini')
        # 备份现有的数据库
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
        # 清空日志文件
        open(temp_file_name, 'w').close()
        self.fid = open(temp_file_name, 'w+')

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

    def log(self, msg):
        if msg[-1] != '\n':
            msg += '\n'
        self.fid.write(msg)

    # 复制一份测试过程中的数据库出来
    def backup_db(self):
        idx = 1
        db_name = os.path.join(os.getcwd(), 'data.db')
        base_name = os.path.join(os.getcwd(), 'data.db.debug')
        new_name = base_name
        while True:
            if not os.path.exists(new_name):
                copyfile(db_name, new_name)
                break
            else:
                new_name = base_name + str(idx)
                idx += 1
# ********************************下面是正式测试用例********************************

    def test_00_init(self):
        # 首先检查网络连通性
        internet = check_connect()
        self.assertTrue(internet)
        # 如果没网，则跳过所有测试
        if not internet:
            sys.stderr.write(u'请检查网络连通性！\n')
            exit(-1)

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
        while True:
            sleep(0.5)
            if server.thread_pool.count_working_thread() == 0:
                break
        # 最后检查所有任务的状态是否是成功
        # 也就是CurrentTask表中是否为空
        self.assertTrue(db.Query(sql)[0][0] == 0)

    def test_06_modify_rules(self):
        post_data = {
            'action': 'modify',
            'TaskID': '',
            'Rule_Name': '',
            'URL_Rule': '',
            'Status': '1'
        }
        s, r = self.login_root()
        r = s.get('http://localhost/modify_rules')
        soup = bs.BeautifulSoup(r.text)
        res = soup.findAll('input', {'type': 'hidden', 'name': 'TaskID'})
        task_id = map(lambda x: str(x['value']), res)
        new_urls = [
            'http://www.test.com/%day%.png',
            'www.test.com/%prev_day%.png',
            'http://www.test.com/%next_day%.png',
            'www.test.com/%year%%mon%%day%.png',
            'www.test.com/%prev_year%%next_mon%%day%.png'
        ]
        self.assertTrue(len(task_id) == len(new_urls))
        for idx in xrange(len(new_urls)):
            post_data['TaskID'] = task_id[idx]
            post_data['Rule_Name'] = u'测试修改规则' + str(idx + 1)
            post_data['URL_Rule'] = new_urls[idx]
            r = s.post('http://localhost/modify_rules', post_data)
            self.assertTrue('200' in r.text)
        # 最后再检查一下规则名称是否被成功修改
        r = s.get('http://localhost/modify_rules')
        self.assertTrue(u'测试修改规则' in r.text)

    def test_07_check_keywords(self):
        s, r = self.login_root()
        # 这个测试是检查线程功能是否正确
        num_tasks = 5
        # 创建一个下载服务器
        server = DownloadServer(True)
        # 首先更新当前任务
        server.update_calendar()
        # 检查当前任务表中是否出现了足够的任务
        sql = "SELECT COUNT(`TaskID`) FROM `CurrentTask`"
        self.assertTrue(db.Query(sql)[0][0] == num_tasks)
        # 此时所有任务应该都在等待
        r = s.get('http://localhost/modify_tasks')
        self.assertTrue(r.text.count(u'等待中') == 5)
        soup = bs.BeautifulSoup(r.text)
        # 获取所有任务的保存位置
        locations = map(lambda x: x.renderContents().strip('\n'),
                        soup.findAll('td', {'id': 'SavePos'}))
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
        while True:
            sleep(0.5)
            if server.thread_pool.count_working_thread() == 0:
                break
        # 最后检查所有任务的状态是否是成功
        # 也就是CurrentTask表中是否为空
        self.assertTrue(db.Query(sql)[0][0] == 0)
        # 然后把所有文件中的内容打印出来
        # 内容就是下载用的命令
        for loc in locations:
            data = open(loc.decode('utf-8'), 'r').read()
            self.log(data)

    def test_08_del_prev_rules(self, lenTaskIDs=5):
        # 这个case是要删除掉先前的所有规则
        s, r = self.login_root()
        r = s.get('http://localhost/modify_rules')
        # 通过解析页面的方式获取任务ID
        soup = bs.BeautifulSoup(r.text)
        res = soup.findAll('input', {'type': 'hidden', 'name': 'TaskID'})
        TaskIDs = map(lambda x: str(x['value']), res)
        self.assertTrue(len(TaskIDs) == lenTaskIDs)
        for ID in TaskIDs:
            post_data = {
                'action': 'delete',
                'TaskID': ID
            }
            r = s.post('http://localhost/modify_rules', post_data)
            self.assertTrue('200' in r.text)
        # 再次读取规则页面，检查所有规则是否都被删除
        r = s.get('http://localhost/modify_rules')
        soup = bs.BeautifulSoup(r.text)
        res = soup.findAll('input', {'type': 'hidden', 'name': 'TaskID'})
        self.assertTrue(len(res) == 0)

    def test_09_modify_system_settings(self):
        s, r = self.login_root()
        post_data = {
            'action': 'config',
            'SiteName': u'超级下载器',
            'GlobalPos': cfg.read('global_pos'),
            'PortName': '',
            'DateCheckingInterval': '601',
            'WorkerCheckingInterval': '4',
            'CleanerCheckingInterval': '86401',
            'MaxThreads': '10',
            'MaxBuf': '1024'
        }
        # 测数据无效的情况
        r = s.post('http://localhost/admin', post_data)
        self.assertTrue('400' in r.text)
        # 测操作合法的情况
        post_data['PortName'] = '80'
        r = s.post('http://localhost/admin', post_data)
        self.assertTrue('200' in r.text)
        self.assertTrue(cfg.read('max_threads') == '10')
        self.assertTrue(cfg.read('max_buf') == '1024')
        self.assertTrue(cfg.read('date_checking_interval') == '601')
        self.assertTrue(cfg.read('worker_checking_interval') == '4')
        self.assertTrue(cfg.read('cleaner_checking_interval') == '86401')

    def test_10_full_press_test(self):
        num_tasks = int(cfg.read('max_threads')) + 5
        # 增加大量任务
        s, r = self.login('test01', '12345678')
        # 确认正确登录
        self.assertTrue(u'管理规则' in r.text)
        tz = 'UTC'
        post_url = 'http://localhost/modify_rules'
        post_data = data_modify_rule
        now = datetime.now(timezone(tz))
        # 先批量增加规则
        for i in xrange(num_tasks):
            test_name = u'压力测试' + str(i + 1)
            post_data['RepeatType'] = 'day'
            post_data['Weekday'] = now.isoweekday()
            post_data['hour'][0] = str(now.hour)
            post_data['minute'][0] = str(now.minute)
            post_data['Rule_Name'] = test_name
            post_data['Sub_Dir'] = test_name
            post_data['TimeZone'] = tz
            r = s.post(post_url, data=post_data)
            # 检查操作是否成功
            self.assertTrue('200' in r.text)
            # 检查是否生成了对应的目录
            self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test01', test_name)))
        # 创建下载服务器（调试模式）
        server = DownloadServer(True)
        # 首先更新当前任务
        server.update_calendar()
        # 检查当前任务表中是否出现了足够的任务
        sql = "SELECT COUNT(`TaskID`) FROM `CurrentTask`"
        self.assertTrue(db.Query(sql)[0][0] == num_tasks)
        # 然后将任务加载到缓冲区，检查是否出现了正确数量的任务
        server.update_worker()
        self.assertTrue(len(server.thread_pool.working_queue) == num_tasks)
        # 接下来启动线程池
        server.thread_pool.start()
        # 检查任务缓冲区中的元素数量
        sleep(0.2)
        self.assertTrue(len(server.thread_pool.working_queue) == 5)
        # 检查线程池中是否启动了正确数量的线程
        sleep(0.2)
        self.assertTrue(server.thread_pool.count_working_thread() == int(cfg.read('max_threads')))
        # 还是要等待所有线程结束才行，不然数据库有锁
        while True:
            sleep(0.5)
            if server.thread_pool.count_working_thread() == 0:
                break
        # 最后检查所有任务的状态是否是成功
        # 也就是CurrentTask表中是否为空
        self.assertTrue(db.Query(sql)[0][0] == 0)

    def test_11_modify_user_by_self(self):
        s, r = self.login('test01', '12345678')
        # 首先测试更改常规信息
        post_data = {
            'UserName': u'侯颖琳',
            'Tel': '15689100026',
            'E-mail': '123@qq.com',
            'MaxFiles': '1124',
            'MaxSize': '',
            'NameRule': 'default',
            'Downloader': 'aria2',
            'OldPassWord': '12345678',
            'NewPassWord': '1994.2.21'
        }
        r = s.post('http://localhost/settings', post_data)
        self.assertTrue(u'是否合法' in r.text)
        post_data['MaxSize'] = '1224'
        post_data['OldPassWord'] = ''
        r = s.post('http://localhost/settings', post_data)
        self.assertTrue(u'密码错误' in r.text)
        post_data['OldPassWord'] = '12345678'
        r = s.post('http://localhost/settings', post_data)
        self.assertTrue(u'操作成功' in r.text)
        sql = "SELECT `PassWord`, `UserName`, `MaxSize` FROM Users WHERE UID = 'test01'"
        self.assertTrue(db.Query(sql)[0][0] == '1994.2.21')
        self.assertTrue(db.Query(sql)[0][1] == r'侯颖琳')
        self.assertTrue(db.Query(sql)[0][2] == 1224)

    def test_12_modify_user_by_admin(self):
        post_data = {
            'action': 'modify',
            'UID': 'test02',
            'UserName': u'侯颖琳是二货',
            'PassWord': '3.1415926',
            'MaxFiles': '5',
            'MaxSize': '1'
        }
        s, r = self.login_root()
        r = s.post('http://localhost/admin', post_data)
        self.assertTrue('200' in r.text)
        sql = "SELECT `UserName`, `MaxFiles`, `MaxSize`," \
              "`PassWord` FROM `Users` WHERE `UID` = '%s'" % 'test02'
        self.assertTrue(db.Query(sql)[0][0] == r'侯颖琳是二货')
        self.assertTrue(db.Query(sql)[0][1] == 5)
        self.assertTrue(db.Query(sql)[0][2] == 1)
        self.assertTrue(db.Query(sql)[0][3] == '3.1415926')

    def test_13_del_user_by_admin(self):
        post_data = {
            'action': 'delete',
            'UID': 'test01',
            'UserName': u'黄',
            'PassWord': '12345678',
            'MaxFiles': '1234',
            'MaxSize': '1234'
        }
        s, r = self.login_root()
        # 先删除一个用户
        r = s.post('http://localhost/admin', post_data)
        self.assertTrue('200' in r.text)
        # 然后检查数据库
        sql1 = "SELECT COUNT(`UID`) FROM Users WHERE `UID` = 'test01'"
        sql2 = "SELECT COUNT(`UID`) FROM Users WHERE `UID` = 'test02'"
        sql3 = "SELECT COUNT(`TaskID`) FROM UserTask WHERE `UID` = 'test01'"
        sql4 = "SELECT COUNT(`TaskID`) FROM UserTask WHERE `UID` = 'test02'"
        self.assertTrue(db.Query(sql1)[0][0] == 0)
        self.assertTrue(db.Query(sql2)[0][0] == 1)
        # 保证数据库中没有相应的任务
        self.assertTrue(db.Query(sql3)[0][0] == 0)
        self.assertTrue(db.Query(sql4)[0][0] == 0)
        # 并且也已经删除了所有文件夹
        self.assertFalse(os.path.exists(os.path.join(cfg.read('global_pos'), 'test01')))
        self.assertTrue(os.path.exists(os.path.join(cfg.read('global_pos'), 'test02')))

    def test_14_disk_quota_01(self):
        num_tasks = 5
        s, r = self.login('test02', '3.1415926')
        # 确认正确登录
        self.assertTrue(u'管理规则' in r.text)
        tz = 'UTC'
        post_url = 'http://localhost/modify_rules'
        post_data = data_modify_rule
        now = datetime.now(timezone(tz))
        # 先批量增加规则
        for i in xrange(num_tasks):
            test_name = u'磁盘配额测试' + str(i + 1)
            post_data['RepeatType'] = 'day'
            post_data['Weekday'] = now.isoweekday()
            post_data['hour'][0] = str(now.hour)
            post_data['minute'][0] = str(now.minute)
            post_data['Rule_Name'] = test_name
            post_data['Sub_Dir'] = test_name
            post_data['TimeZone'] = tz
            r = s.post(post_url, data=post_data)
            # 检查操作是否成功
            self.assertTrue('200' in r.text)
            # 检查是否生成了对应的目录
            self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test02', test_name)))
        # 创建下载服务器（调试模式）
        server = DownloadServer(True)
        # 首先更新当前任务
        server.update_calendar()
        # 然后将任务加载到缓冲区，检查是否出现了正确数量的任务
        server.update_worker()
        # 接下来启动线程池
        server.thread_pool.start()
        # 等待所有线程退出
        while True:
            sleep(0.5)
            if server.thread_pool.count_working_thread() == 0:
                break
        server.clean_worker()
        sql = "SELECT COUNT(`TaskID`) FROM `UserTask` WHERE `UID` = 'test02' AND Status = 0"
        # 应该不会触发清理
        self.assertTrue(db.Query(sql)[0][0] == 0)

    def test_14_disk_quota_02(self):
        s, r = self.login('test02', '3.1415926')
        # 确认正确登录
        self.assertTrue(u'管理规则' in r.text)
        tz = 'UTC'
        post_url = 'http://localhost/modify_rules'
        post_data = data_modify_rule
        now = datetime.now(timezone(tz))
        # 先批量增加一条新规则
        test_name = u'磁盘配额测试6'
        post_data['RepeatType'] = 'day'
        post_data['Weekday'] = now.isoweekday()
        post_data['hour'][0] = str(now.hour)
        post_data['minute'][0] = str(now.minute)
        post_data['Rule_Name'] = test_name
        post_data['Sub_Dir'] = test_name
        post_data['TimeZone'] = tz
        r = s.post(post_url, data=post_data)
        # 检查操作是否成功
        self.assertTrue('200' in r.text)
        # 检查是否生成了对应的目录
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test02', test_name)))
        # 创建下载服务器（调试模式）
        server = DownloadServer(True)
        # 首先更新当前任务
        server.update_calendar()
        # 然后将任务加载到缓冲区，检查是否出现了正确数量的任务
        server.update_worker()
        # 接下来启动线程池
        server.thread_pool.start()
        # 等待所有线程退出
        while True:
            sleep(0.5)
            if server.thread_pool.count_working_thread() == 0:
                break
        server.clean_worker()
        sql = "SELECT COUNT(`TaskID`) FROM `UserTask` WHERE `UID` = 'test02' AND Status = 0"
        # 这次应该会触发清理
        self.assertTrue(db.Query(sql)[0][0] == 6)
        sql = "SELECT COUNT(`TaskID`) FROM `CurrentTask` WHERE `UID` = 'test02'"
        self.assertTrue(db.Query(sql)[0][0] == 0)

    def test_15_real_download_test(self):
        # 首先删除所有先前的规则以及文件
        self.test_08_del_prev_rules(6)
        # TODO: 测试三个下载器能否都正确覆盖文件
        s, r = self.login('test02', '3.1415926')
        # 确认正确登录
        self.assertTrue(u'管理规则' in r.text)
        tz = 'UTC'
        post_url = 'http://localhost/modify_rules'
        post_data = data_modify_rule
        now = datetime.now(timezone(tz))
        # 先批量增加三条新规则
        downloader = ['aria2', 'wget', 'python', 'aria2']
        for idx, dwn in enumerate(downloader):
            test_name = u'任务覆盖测试' + str(idx + 1)
            post_data['RepeatType'] = 'day'
            post_data['Weekday'] = now.isoweekday()
            post_data['hour'][0] = str(now.hour)
            post_data['minute'][0] = str(now.minute)
            post_data['Rule_Name'] = test_name
            post_data['Sub_Dir'] = test_name
            if idx == 3: post_data['Sub_Dir'] = ''
            post_data['TimeZone'] = tz
            post_data['Downloader'] = dwn
            post_data['URL_Rule'] = 'www.baidu.com/img/bdlogo.png'
            post_data['NameRule'] = 'rule'
            r = s.post(post_url, data=post_data)
            # 检查操作是否成功
            self.assertTrue('200' in r.text)
            # 检查是否生成了对应的目录
            self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test02', test_name if idx != 3 else '')))
        # 创建下载服务器（正常模式）
        server = DownloadServer()
        # 首先更新当前任务
        server.update_calendar()
        # 此时所有任务应该都在等待
        r = s.get('http://localhost/modify_tasks')
        self.assertTrue(r.text.count(u'等待中') == 4)
        soup = bs.BeautifulSoup(r.text)
        # 获取所有任务的保存位置
        locations = map(lambda x: x.renderContents().strip('\n').decode('utf-8'),
                        soup.findAll('td', {'id': 'SavePos'}))
        # 然后将任务加载到缓冲区
        server.update_worker()
        # 接下来启动线程池
        server.thread_pool.start()
        # 等待所有线程退出
        while True:
            sleep(0.5)
            if server.thread_pool.count_working_thread() == 0:
                break
        # 检查所有文件是否下载成功
        time_stamps = {}
        self.assertTrue(len(locations) == 4)
        for pos in locations:
            self.assertTrue(imghdr.what(pos) is not None)
            time_stamps[pos] = os.path.getmtime(pos)
        # 然后重新下载
        server.prev_day = {}
        server.update_calendar()
        server.update_worker()
        # 等待所有线程退出
        while True:
            sleep(0.5)
            if server.thread_pool.count_working_thread() == 0:
                break
        for pos in locations:
            self.assertTrue(imghdr.what(pos).lower() == 'png')
            # 确认文件被覆盖，即变得更新
            self.assertTrue(os.path.getmtime(pos) > time_stamps[pos])


if __name__ == '__main__':
    unittest.main()
