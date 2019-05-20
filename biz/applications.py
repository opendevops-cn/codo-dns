#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Author : shenshuo
date   : 2019年5月6日
role   : Application
"""

import json
from websdk.application import Application as myApplication
from biz.handlers.domain_handler import domain_urls
from models.domain import DNSDomainConf
from websdk.db_context import DBContext


class Application(myApplication):
    def __init__(self, **settings):
        self.conf_init(**settings)
        self.region_init(**settings)
        urls = []
        urls.extend(domain_urls)
        super(Application, self).__init__(urls, **settings)

    ### 初始化配置
    def conf_init(self, **settings):
        with DBContext('w', None, True, **settings) as session:
            is_exist = session.query(DNSDomainConf.id).filter(DNSDomainConf.conf_name == 'conf_init').first()

            if is_exist:
                return

            named_init_conf = settings['named_init_conf']
            session.add(DNSDomainConf(conf_name='conf_init', conf_value=str(named_init_conf)))

    ### 初始化区域
    def region_init(self, **settings):
        with DBContext('w', None, True, **settings) as session:
            is_exist = session.query(DNSDomainConf.id).filter(DNSDomainConf.conf_name == 'region_init').first()

            if is_exist:
                return

            region_init_conf = settings['region_init_conf']
            session.add(DNSDomainConf(conf_name='region_init', conf_value=json.dumps(region_init_conf)))


if __name__ == '__main__':
    pass
