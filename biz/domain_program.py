#!/usr/bin/env python
# -*- coding: utf-8 -*-


from tornado import ioloop
from websdk.application import Application as myApplication
from biz.cloud_domain import all_sync_index


class Application(myApplication):
    def __init__(self, **settings):
        urls = []
        program_callback = ioloop.PeriodicCallback(all_sync_index, 3600000)  # 1小时 3600000
        program_callback.start()
        super(Application, self).__init__(urls, **settings)


if __name__ == '__main__':
    pass
