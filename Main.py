# -*- coding: UTF-8 -*-

__author__ = 'FinalTheory'

from WebServer import start_web_server
from DownloadServer import DownloadServer


if __name__ == '__main__':
    # 首先实例化并启动一个下载服务器
    DownloadServer().start()
    start_web_server()
