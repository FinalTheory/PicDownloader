# -*- coding: UTF-8 -*-

__author__ = 'FinalTheory'

import socket
socket.setdefaulttimeout(5)
import os
import sys
from dateutil import parser
from time import sleep
from datetime import datetime, timedelta
from pytz import timezone
from ThreadPool import ThreadPool
from thread import start_new_thread
from Tools import db, cfg, get_dir_size
from GlobalDefs import *


class DownloadServer():
    def __init__(self):
        self.prev_day = {}
        self.thread_pool = ThreadPool(
            int(cfg.read('max_threads')),
            int(cfg.read('max_buf')),
            cfg.read('downloader'),
        )
        # 注意先清空先前留下的下载任务
        db.Execute("DELETE FROM `CurrentTask`")

    def start(self):
        # 首先启动线程池所有线程
        self.thread_pool.start()
        # 然后启动日历线程更新任务列表
        start_new_thread(self.calendar_daemon, ())
        # 同时启动生产者线程
        start_new_thread(self.worker_daemon, ())
        # 最后启动配额管理线程
        start_new_thread(self.cleaner_daemon, ())

    # 这个方法对于每个任务，判断是否进入了新的一天
    # 如果是的话，就将新的任务增加到任务列表中
    def update_calendar(self, overwrite_time=None):
        # 注意同一个规则所实例化的任务，只能被添加一次
        sql = "SELECT * FROM `UserTask` WHERE " \
              "`TaskID` NOT IN (SELECT `TaskID` FROM `CurrentTask`) " \
              "AND `Status` != 0"
        this_day = {}
        all_tasks = db.Query(sql)
        for task in all_tasks:
            # 首先读取时区信息，并转换为当前任务所在时区的时间
            TimeZone = timezone(str(task[6]))
            if overwrite_time is None:
                today = datetime.now(TimeZone)
            else:
                today = overwrite_time

            # 然后判断在该时区是否进入了新的一天
            is_new_day = False
            if self.prev_day.get(TimeZone, None) is None \
                    or today.day != self.prev_day[TimeZone]:
                this_day[TimeZone] = today.day
                is_new_day = True

            # 如果确实进入了新的一天
            if is_new_day:
                # 首先生成任务开始和结束时间
                # 同样注意转换为任务所在的时区
                date_nums = map(int, task[5].split())
                StartTime = datetime(year=today.year,
                                     month=today.month,
                                     day=today.day,
                                     hour=date_nums[3],
                                     minute=date_nums[4],
                                     tzinfo=TimeZone)
                FinishTime = StartTime + timedelta(hours=task[10])

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
                # 生成URL后，更新文件保存位置：
                # 1. 首先读取全局位置
                Location = cfg.read('global_pos')
                # 2. 然后定位到用户家目录位置
                Location = os.path.join(Location, UID)
                # 3. 再定位到规则目录位置，这里的类型都是str
                RuleName = task[3]
                SubDir = task[8]
                if SubDir:
                    Location = os.path.join(Location, SubDir)
                # 4. 最后根据命名规则确定文件名
                if task[9] == 'auto':
                    Location = os.path.join(Location, URL.split('/')[-1])
                else:
                    Location = os.path.join(Location, RuleName + '.' + URL.split('.')[-1])

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
        self.prev_day = this_day

    # 这个方法定时检查任务列表
    # 将过期的任务从任务列表中删除
    # 将未过期的任务添加到下载线程池
    # 任务被重试的次数越多，则下载优先级越低
    def update_worker(self, overwrite_time=None):
        # TODO: 添加任务前先检查当前网络是否连通
        # 首先选择所有任务列表中未暂停且未被下载中的任务
        sql = "SELECT * FROM `CurrentTask` WHERE `Status` = 1 ORDER BY `RepeatTimes` ASC"
        all_task = db.Query(sql)
        # 对于每一项任务进行处理，加入缓冲区
        for task in all_task:
            # 利用任务的时区信息，实例化两个时间戳
            # 并且计算当前时刻在目标时区是几点
            TimeZone = timezone(task[7])
            if overwrite_time is None:
                Now = datetime.now(TimeZone)
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
                sql = "SELECT `Downloader`, `CheckType`, `CheckSize` FROM `UserTask` WHERE `TaskID` = %d" % TaskID
                task_data = db.QueryFirst(sql)
                data = {
                    'TaskID': TaskID,
                    'URL': task[1],
                    # 注意这里的编码，需要传入unicode
                    'Location': task[3].decode('utf-8'),
                    'Downloader': task_data[0],
                    'CheckType': task_data[1],
                    'CheckSize': task_data[2]
                }
                self.thread_pool.insert(data)

    # 简而言之，实现一个文件配额功能
    # 由于用户文件分目录保存，因此就不用新建数据库结构了
    def clean_worker(self):
        sql = "SELECT `UID`, `MaxSize`, `MaxFiles` FROM `Users`"
        all_users = db.Query(sql)
        base_dir = cfg.read('global_pos')
        for user in all_users:
            UID = user[0]
            MaxSize = user[1]
            MaxFiles = user[2]
            user_home_dir = os.path.join(base_dir, UID)
            TotalSize, TotalFiles = get_dir_size(user_home_dir)
            TotalSize /= (1024 * 1024)
            # 如果超出了文件数量配额或者文件大小配额
            if TotalSize > MaxSize or TotalFiles > MaxFiles:
                # 首先暂停该用户所有任务
                sql = "UPDATE `UserTask` SET `Status` = 0 WHERE `UID` = %s" % UID
                db.Execute(sql)
                # 其次删除所有正在进行的任务
                sql = "DELETE FROM `CurrentTask` WHERE `UID` = %s" % UID
                db.Execute(sql)

    # “生产者”函数的守护线程
    def worker_daemon(self):
        sys.stderr.write('Worker daemon of Download Server started!\n')
        while True:
            sleep(int(cfg.read('worker_checking_interval')))
            self.update_worker()

    # 维护任务列表的方法的守护线程
    def calendar_daemon(self):
        sys.stderr.write('Calendar daemon of Download Server started!\n')
        while True:
            self.update_calendar()
            sleep(int(cfg.read('date_checking_interval')))

    def cleaner_daemon(self):
        while True:
            sleep(int(cfg.read('cleaner_checking_interval')))
            self.clean_worker()