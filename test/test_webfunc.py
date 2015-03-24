# -*- coding: UTF-8 -*-
__author__ = 'FinalTheory'

import os
import unittest
import BeautifulSoup as bs
from pytz import timezone
import requests
from .. Tools import cfg, db
from .. WebServer import start_web_server
from thread import start_new_thread
from datetime import datetime
from shutil import copyfile, rmtree
from tempfile import mkdtemp


# TODO: 增加完善的单元测试
# 主要测试的内容：
# 1. 用户登录、修改个人信息等功能，以及其异常处理
# 2. 管理员登录、用户管理、系统全局设置等
# 3. 下载任务的更新、处理等，重点测试对时区的支持
# 4. 线程池的并发性测试？能做吗？


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
    'RepeatType': 'day',
    'Weekday': '1',
    'year': '',
    'month': ['', ''],
    'day': ['', '', ''],
    'hour': ['0', '', '', '', ''],
    'minute': ['0', '', '', '', ''],
    # 任务状态
    'Status': '1',
    # 时区
    'TimeZone': 'UTC',
    # 其他一些设置
    'NameRule': 'auto',
    'Downloader': 'aria2',
    'TaskTime': '12',
    'CheckType': 'auto',
    'CheckSize': '4096'
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
    def __init__(self, *args, **kwargs):
        super(TestWebFunction, self).__init__(*args, **kwargs)

    # 返回以管理员登录后的session以及信息
    def login_root(self):
        s = requests.Session()
        post_url = 'http://localhost/login'
        post_data = {
            'UID': 'root',
            'password': '3.1415926',
            'expires': '31536000'
        }
        r = s.post(post_url, data=post_data)
        return s, r

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
        pass

    def test_03_add_rule_01(self):
        s, r = self.login_root()
        post_url = 'http://localhost/modify_rules'
        post_data = data_modify_rule
        # 保证这个任务处于有效时间段内
        tz = 'UTC'
        test_name = u'测试01'
        now = datetime.now(timezone(tz))
        post_data['hour'][0] = str(now.hour)
        post_data['Rule_Name'] = test_name
        post_data['Sub_Dir'] = test_name
        post_data['minute'][0] = str(now.minute)
        r = s.post(post_url, data=post_data)
        # 检查操作是否成功
        self.assertTrue('200' in r.text)
        # 检查是否生成了对应的目录
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'root', test_name)))

    def test_04_add_rule_02(self):
        pass

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