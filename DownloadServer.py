# -*- coding: UTF-8 -*-

__author__ = 'FinalTheory'

import os
import sys
from dateutil import parser
from time import sleep
from datetime import datetime, timedelta
from pytz import timezone
from ThreadPool import ThreadPool
from thread import start_new_thread
from Tools import db, cfg
from GlobalDefs import *


class DownloadServer():
    def __init__(self):
        self.prev_day = {}
        self.thread_pool = ThreadPool(
            int(cfg.read('max_threads')),
            int(cfg.read('max_buf')),
            cfg.read('downloader'),
            cfg.read('check_if_success'),
            int(cfg.read('size_if_success'))
        )

    def start(self):
        # 首先启动线程池所有线程
        self.thread_pool.start()
        # 然后启动日历线程更新任务列表
        start_new_thread(self.calendar_daemon, ())
        # 同时启动生产者线程
        start_new_thread(self.worker_daemon, ())

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

    # TODO: 增加一个清理线程以及其Daemon，用来清理超过数量/大小的用户文件
    # 简而言之，实现一个文件配额功能
    # 数据表结构：UID, 文件位置, 下载时间戳
    def cleaner(self):
        pass

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