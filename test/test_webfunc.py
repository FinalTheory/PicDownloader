# -*- coding: UTF-8 -*-
__author__ = 'FinalTheory'

# TODO: 增加完善的单元测试
# 主要测试的内容：
# 1. 用户登录、修改个人信息等功能，以及其异常处理
# 2. 管理员登录、用户管理、系统全局设置等
# 3. 下载任务的更新、处理等，重点测试对时区的支持
# 4. 线程池的并发性测试？能做吗？

import unittest

class BasicTest(unittest.TestCase):
    # 类初始化和清理函数
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

class TestWebFunction(BasicTest):
    pass


if __name__ == '__main__':
    unittest.main()