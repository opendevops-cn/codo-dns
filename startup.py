#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019年5月6日
Desc    : 启动文件
"""

import fire
from tornado.options import define
from websdk.program import MainProgram
from settings import settings as app_settings
from biz.applications import Application as DNSApi
from biz.domain_program import Application as DNSCron

define("service", default='api', help="start service flag", type=str)


class MyProgram(MainProgram):
    def __init__(self, service='dns', progress_id='dns'):
        self.__app = None
        settings = app_settings
        if service == 'dns':
            self.__app = DNSApi(**settings)
        elif service == 'dns_cron':
            self.__app = DNSCron(**settings)

        super(MyProgram, self).__init__(progress_id)
        self.__app.start_server()


if __name__ == '__main__':
    fire.Fire(MyProgram)
