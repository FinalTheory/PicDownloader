# -*- coding: UTF-8 -*-
# 在本文件中定义了线程池以及相关类型
__author__ = 'FinalTheory'

import os
import imghdr
import requests
import certifi
from datetime import datetime
from threading import Semaphore, Lock
from thread import start_new_thread
from Tools import db, log
from subprocess import call
from collections import deque
from time import sleep
from urllib import urlretrieve
from random import random


class BasicDownloader:
    def __init__(self,
                 URL,
                 Location,
                 TaskID,
                 check_type,
                 check_size,
                 is_debug):
        sql = "UPDATE `CurrentTask` SET `Status` = 2 WHERE `TaskID` = %d" % TaskID
        db.Execute(sql)
        self.download(URL, Location, is_debug)
        status = self.check_if_success(Location, check_type, check_size, is_debug)
        if status:
            # 若下载成功，则从未完成列表中删除
            sql = "DELETE FROM `CurrentTask` WHERE `TaskID` = %d" % TaskID
            log.log_message(u'[INFO] Task %d downloaded successfully to %s at %s'
                            % (TaskID, Location, datetime.now().ctime()))
        else:
            # 首先删除下载失败的文件
            if os.path.exists(Location):
                os.remove(Location)
            # 然后将其下载次数+1以降低优先级，并且恢复正常状态
            sql = "UPDATE `CurrentTask` SET `RepeatTimes` = `RepeatTimes` + 1, " \
                  "`Status` = 1 WHERE `TaskID` = %d" % TaskID
            log.log_message(u'[INFO] Task %d download to %s failed at %s'
                            % (TaskID, Location, datetime.now().ctime()))
        db.Execute(sql)

    def download(self, URL, Location, is_debug):
        pass

    def check_if_success(self, Location, check_type, check_size, is_debug):
        # 调试模式下，直接认为下载成功
        if is_debug:
            return True

        # 首先检查文件是否存在
        if not os.path.exists(Location):
            return False

        # 然后有两种判断下载是否成功的方法：
        # 1. 用内置的库读取文件头，从而判断是否成功
        # 2. 检查文件大小，如果大于预设的尺寸，则认为下载成功
        # 3. 调试模式下不检查，直接返回成功
        if check_type == 'auto':
            if imghdr.what(Location) is None:
                return False
            else:
                return True
        elif check_type == 'size':
            if os.path.getsize(Location) > int(check_size):
                return True
            else:
                return False


class Aria2Downloader(BasicDownloader):
    def download(self, URL, Location, is_debug):
        cmd = [u'aria2c', URL,
               u'--dir=%s' % Location[0:Location.rfind(os.path.sep)],
               u'--out=%s' % Location.split(os.path.sep)[-1],
               u'--max-connection-per-server=3',
               u'--allow-overwrite=true']
        if is_debug:
            # 如果处于多线程调试模式
            # 则线程挂起随机的时间，模拟下载过程
            sleep(random()+1)
            # 然后将下载的命令行写入对应文件
            with open(Location, 'w') as fid:
                data = ' '.join(cmd)
                if type(data) == unicode:
                    data = data.encode('gb18030')
                fid.write(data)
        else:
            cmd = ' '.join(cmd)
            if type(cmd) == unicode:
                cmd = cmd.encode('gb18030')
            try:
                call(cmd, shell=True)
            except Exception:
                log.log_message(u"[ERROR] '%s' execution failed!" % cmd)


class WgetDownloader(BasicDownloader):
    def download(self, URL, Location, is_debug):
        cmd = [u'wget', URL,
               u'--output-document=%s' % Location,
               u'--no-check-certificate']
        if is_debug:
            # 如果处于多线程调试模式
            # 则线程挂起随机的时间，模拟下载过程
            sleep(random()+1)
            # 然后将下载的命令行写入对应文件
            with open(Location, 'w') as fid:
                data = ' '.join(cmd)
                if type(data) == unicode:
                    data = data.encode('gb18030')
                fid.write(data)
        else:
            cmd = ' '.join(cmd)
            if type(cmd) == unicode:
                cmd = cmd.encode('gb18030')
            try:
                call(cmd, shell=True)
            except Exception:
                log.log_message(u"[ERROR] '%s' execution failed!" % cmd)


class PythonDownloader(BasicDownloader):
    def download(self, URL, Location, is_debug):
        if is_debug:
            # 如果处于多线程调试模式
            # 则线程挂起随机的时间，模拟下载过程
            sleep(random()+1)
            # 然后将下载的命令行写入对应文件
            with open(Location, 'w') as fid:
                data = ' '.join(u'request.get() "%s" to "%s"' % (URL, Location))
                if type(data) == unicode:
                    data = data.encode('gb18030')
                fid.write(data)
        else:
            # 首先获取程序的根路径
            try:
                approot = os.path.dirname(os.path.abspath(__file__))
            except NameError:
                import sys
                approot = os.path.dirname(os.path.abspath(sys.argv[0]))
            # 然后开始下载
            try:
                cert_root = os.path.join(approot, '..', 'cacert.pem')
                if not os.path.exists(cert_root):
                    cert_root = certifi.where()
                r = requests.get(URL, verify=cert_root)
                with open(Location, "wb") as fid:
                    fid.write(r.content)
            except Exception as err:
                log.log_message(u"[ERROR] 'request.get()' to '%s' execution failed! %s" % (Location, err))


class ThreadPool:
    def __init__(self,
                 is_debug=False,
                 max_threads=32,
                 max_buf=4096):
        # 定义锁以及相关变量
        self.max_threads = max_threads
        self.working_queue = deque()
        self.thread_locks = []
        # 线程需要用到的公共变量
        self.is_debug = is_debug
        # 最后是三个信号量
        self.slots = Semaphore(max_buf)
        self.items = Semaphore(0)
        self.mutex = Lock()

    # 这个函数用来查看当前正在工作的线程
    def count_working_thread(self):
        count = 0
        for i in xrange(self.max_threads):
            # 非阻塞地尝试获取线程的锁
            # 如果能够得到，则这个线程未在工作
            if self.thread_locks[i].acquire(False):
                count += 1
                self.thread_locks[i].release()
        return self.max_threads - count

    def work_thread(self, my_idx):
        while True:
            sleep(0.1)
            data = self.remove()
            # 先对线程加锁，用来确认是否工作中
            self.thread_locks[my_idx].acquire()
            # 从缓冲区中抓取任务并执行下载
            if data['Downloader'] == 'python':
                PythonDownloader(data['URL'],
                                 data['Location'],
                                 data['TaskID'],
                                 data['CheckType'],
                                 data['CheckSize'],
                                 self.is_debug)
            elif data['Downloader'] == 'wget':
                WgetDownloader(data['URL'],
                                 data['Location'],
                                 data['TaskID'],
                                 data['CheckType'],
                                 data['CheckSize'],
                                 self.is_debug)
            elif data['Downloader'] == 'aria2':
                Aria2Downloader(data['URL'],
                                 data['Location'],
                                 data['TaskID'],
                                 data['CheckType'],
                                 data['CheckSize'],
                                 self.is_debug)
            self.thread_locks[my_idx].release()

    # 下面两个方法用于暂停和恢复所有下载线程
    # 由于请求锁的过程中可能会被阻塞，因此需要启动新线程来调用！
    def pause_all_threads(self):
        for idx in xrange(self.max_threads):
            self.thread_locks[idx].acquire()

    def continue_all_threads(self):
        for idx in xrange(self.max_threads):
            self.thread_locks[idx].release()

    # 下面的两个方法用于向缓冲区中插入和删除元素
    def insert(self, data):
        # 插入元素前，首先要保证有空余位置
        self.slots.acquire()
        self.mutex.acquire()
        self.working_queue.append(data)
        self.mutex.release()
        self.items.release()

    def remove(self):
        self.items.acquire()
        self.mutex.acquire()
        result = self.working_queue.popleft()
        self.mutex.release()
        self.slots.release()
        return result

    def start(self):
        # 开始初始化并启动所有线程
        for idx in xrange(self.max_threads):
            self.thread_locks.append(Lock())
            start_new_thread(self.work_thread, (idx,))