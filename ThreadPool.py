# -*- coding: UTF-8 -*-
# 在本文件中定义了线程池以及相关类型
__author__ = 'FinalTheory'

from threading import Thread, Semaphore, Lock
from thread import start_new_thread
from Tools import db
from subprocess import call
from collections import deque
from time import sleep
from urllib import urlretrieve
import imghdr
import os

class BasicDownloader:
    def __init__(self, URL, Location, TaskID, check_type, check_size, is_debug=False):
        self.download(URL, Location, is_debug)
        status = self.check_if_success(Location, check_type, check_size)
        if status:
            # 若下载成功，则从未完成列表中删除
            sql = "DELETE FROM `CurrentTask` WHERE `TaskID` = %d" % TaskID
        else:
            # 否则，就将其下载次数+1，降低优先级
            sql = "UPDATE `CurrentTask` SET `RepeatTimes` = `RepeatTimes` + 1 WHERE `TaskID` = %d" % TaskID
        db.Execute(sql)

    def download(self, URL, Location, is_debug):
        pass

    def check_if_success(self, Location, check_type, check_size):
        # 首先检查文件是否存在
        if not os.path.exists(Location):
            return False

        # 然后有两种判断下载是否成功的方法：
        # 1. 用内置的库读取文件头，从而判断是否成功
        # 2. 检查文件大小，如果大于预设的尺寸，则认为下载成功
        if check_type == 'auto':
            if imghdr.what(Location) is None:
                return False
            else:
                return True
        else:
            if os.path.getsize(Location) > int(check_size):
                return True
            else:
                return False

class Aria2Downloader(BasicDownloader):
    def download(self, URL, Location, is_debug):
        cmd = ['aria2.exe', URL,
               '--out=', Location,
               '--max-connection-per-server', '3']
        if is_debug:
            return ' '.join(cmd) + '\n'
        else:
            call(cmd)

class WgetDownloader(BasicDownloader):
    def download(self, URL, Location, is_debug):
        cmd = ['wget.exe', URL,
               '--output-document=', Location]
        if is_debug:
            return ' '.join(cmd) + '\n'
        else:
            call(cmd)

class PythonDownloader(BasicDownloader):
    def download(self, URL, Location, is_debug):
        if is_debug:
            return 'urlretrieve {} to {}\n'.format(URL, Location)
        else:
            urlretrieve(URL, Location)


class ThreadPool:
    def __init__(self,
                 max_threads=32,
                 max_buf=4096,
                 downloader='python',
                 check_type='auto',
                 check_size=4096):
        # 定义锁以及相关变量
        self.max_threads = max_threads
        self.working_queue = deque()
        self.thread_locks = []
        # 线程需要用到的公共变量
        self.downloader = downloader
        self.check_type = check_type
        self.check_size = check_size
        # 最后是三个信号量
        self.slots = Semaphore(max_buf)
        self.items = Semaphore(0)
        self.mutex = Lock()

    def work_thread(self, my_idx):
        while True:
            sleep(0.1)
            self.thread_locks[my_idx].acquire()
            data = self.remove()
            # 从缓冲区中抓取任务并执行下载
            if self.downloader == 'python':
                PythonDownloader(data['URL'], data['Location'], data['TaskID'], self.check_type, self.check_size)
            elif self.downloader == 'wget':
                WgetDownloader(data['URL'], data['Location'], data['TaskID'], self.check_type, self.check_size)
            elif self.downloader == 'aria2':
                Aria2Downloader(data['URL'], data['Location'], data['TaskID'], self.check_type, self.check_size)
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