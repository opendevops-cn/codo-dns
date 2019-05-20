#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/5/6
Desc    :  主控制
"""
import json
import re
from sqlalchemy import or_
from libs.base_handler import BaseHandler
from websdk.base_handler import LivenessProbe
from websdk.db_context import DBContext
from models.domain import DNSDomainName, DNSDomainZone, DNSDomainConf, DNSDomainLog, model_to_dict


def check_contain_chinese(check_str):
    for ch in check_str:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False


def is_ip(ip):
    # p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')

    p = re.compile('^(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|[1-9])\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)$')
    if p.match(ip):
        return True
    else:
        return False


def is_domain(domain):
    domain_regex = re.compile(r'(?:[A-Z0-9_](?:[A-Z0-9-_]{0,247}[A-Z0-9])?\.)+(?:[A-Z]{2,6}|[A-Z0-9-]{2,}(?<!-))\Z',
                              re.IGNORECASE)
    return True if domain_regex.match(domain) else False


class DomainName(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        domain_list = []
        domain_name_list = []
        with DBContext('r') as session:
            if key:
                domain_info = session.query(DNSDomainName).filter(
                    DNSDomainName.domain_name.like('%{}%'.format(key))).all()
            else:
                domain_info = session.query(DNSDomainName).all()

        for msg in domain_info:
            data_dict = model_to_dict(msg)
            data_dict['create_time'] = str(data_dict['create_time'])
            domain_list.append(data_dict)
            domain_name_list.append(data_dict['domain_name'])

        self.write(dict(code=0, msg='获取成功', data=domain_list, domain_name_list=domain_name_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        domain_name = data.get('domain_name')

        if check_contain_chinese(domain_name):
            return self.write(dict(code=-1, msg='域名不能有汉字'))

        with DBContext('w', None, True) as session:
            is_exist = session.query(DNSDomainName.domain_id).filter(DNSDomainName.domain_name == domain_name).first()

            if is_exist:
                return self.write(dict(code=-2, msg='当前域名已经存在'))

            count = session.query(DNSDomainName).count()
            if count > 8:
                return self.write(dict(code=-3, msg='不能添加更多的域名了'))

            session.add(DNSDomainName(domain_name=domain_name))
            # region = session.query(DNSDomainConf.conf_value).filter(DNSDomainConf.conf_name == 'region_init').first()[0]
            # region = json.loads(region)
            # for r in list(region.keys()):
            session.add(DNSDomainZone(zone=domain_name, type='NS', ttl=86400, data='@', region='默认'))
            log_msg = ' 添加新域名 {}'.format(domain_name)
            session.add(DNSDomainLog(domain_name=domain_name, log_data=log_msg))

        self.write(dict(code=0, msg='添加成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        domain_id = data.get('domain_id')
        if not domain_id:
            return self.write(dict(code=1, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            ### log
            domain_info = session.query(DNSDomainName).filter(DNSDomainName.domain_id == domain_id).first()
            log_msg = '删除： {}, 用户：{}'.format(domain_info.domain_name, self.get_current_nickname())
            session.add(DNSDomainLog(domain_name=domain_info.domain_name, log_data=log_msg))

            session.query(DNSDomainName).filter(DNSDomainName.domain_id == domain_id).delete(synchronize_session=False)

        self.write(dict(code=0, msg='删除成功'))

    def put(self, *args, **kwargs):
        return self.write(dict(code=-1, msg='不支持修改'))

    def patch(self, *args, **kwargs):
        # 启用 暂停
        data = json.loads(self.request.body.decode("utf-8"))
        domain_id = data.get('domain_id')
        domain_state = data.get('domain_state')

        if not domain_id or not domain_state:
            return self.write(dict(code=1, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            session.query(DNSDomainName).filter(DNSDomainName.domain_id == domain_id).update(
                {DNSDomainName.domain_state: domain_state})
            ### log
            domain_info = session.query(DNSDomainName).filter(DNSDomainName.domain_id == domain_id).first()
            log_msg = '{}：{}   用户：{}'.format(domain_state, domain_info.domain_name, self.get_current_nickname())
            session.add(DNSDomainLog(domain_name=domain_info.domain_name, log_data=log_msg))

        self.write(dict(code=0, msg='{}成功'.format(domain_state)))


class DomainZone(BaseHandler):
    def get(self, *args, **kwargs):
        zone = self.get_argument('zone', default=None, strip=True)
        key = self.get_argument('key', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=888, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)
        zone_list = []
        if not zone:
            return self.write(dict(code=-1, msg='请选择一个域名'))

        with DBContext('r') as session:
            if key:
                count = session.query(DNSDomainZone).filter(DNSDomainZone.zone == zone).filter(
                    or_(DNSDomainZone.host.like('%{}%'.format(key)), DNSDomainZone.type.like('%{}%'.format(key)),
                        DNSDomainZone.data.like('%{}%'.format(key)),
                        DNSDomainZone.region.like('%{}%'.format(key)))).count()
                zone_info = session.query(DNSDomainZone).filter(DNSDomainZone.zone == zone).filter(
                    or_(DNSDomainZone.host.like('%{}%'.format(key)), DNSDomainZone.type.like('%{}%'.format(key)),
                        DNSDomainZone.data.like('%{}%'.format(key)),
                        DNSDomainZone.region.like('%{}%'.format(key)))).order_by(
                    DNSDomainZone.zone_id).offset(limit_start).limit(int(limit))
            else:
                count = session.query(DNSDomainZone).filter(DNSDomainZone.zone == zone).count()
                zone_info = session.query(DNSDomainZone).filter(DNSDomainZone.zone == zone).order_by(
                    DNSDomainZone.zone_id).offset(limit_start).limit(int(limit))
        for msg in zone_info:
            data_dict = model_to_dict(msg)
            data_dict['update_time'] = str(data_dict['update_time'])
            zone_list.append(data_dict)
        self.write(dict(code=0, msg='获取成功', count=count, data=zone_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        zone = data.get('zone')
        host = data.get('host')
        zone_type = data.get('type')
        ttl = data.get('ttl')
        zone_data = data.get('data')
        region = data.get('region', 'any')

        if zone_type == 'NS':
            if not zone or not zone_type or not ttl or not zone_data or not region:
                return self.write(dict(code=-1, msg='必填参数不能为空'))
        else:
            if not zone or not host or not zone_type or not ttl or not zone_data or not region:
                return self.write(dict(code=-1, msg='必填参数不能为空'))

        if zone_type == 'MX':
            if not data.get('mx'):
                return self.write(dict(code=-2, msg='请设置MX优先级'))

        if host and check_contain_chinese(host) or check_contain_chinese(zone_data):
            return self.write(dict(code=-2, msg='不支持汉字'))

        if zone_type == 'A':
            if not is_ip(zone_data):
                return self.write(dict(code=-3, msg='A记录值 必须为IP'))

        if zone_type == 'CNAME' or zone_type == 'NS':
            if zone_data[-1] == '.':
                zone_data_cname = zone_data[:-1]
            else:
                zone_data_cname = zone_data

            if not is_domain(zone_data_cname):
                if zone_type == 'NS':
                    return self.write(dict(code=-4, msg='NS记录值 必须为域名，且一定可访问，不然会导致整个区域不可用'))
                else:
                    return self.write(dict(code=-4, msg='CNAME记录值 必须为域名'))
            zone_data = zone_data_cname + '.'

        if host and host not in ['@', '*']:
            if host == '.':
                return self.write(dict(code=-5, msg='请使用合法的记录'))
            if host[0] in ['-', '.'] or host[-1] in ['-', '.']:
                return self.write(dict(code=-5, msg='不合法记录'))

            host_check = host.replace('-', '').replace('.', '')
            if not host_check:
                return self.write(dict(code=-5, msg='不合法记录'))

            if not host_check.isalnum():
                return self.write(dict(code=-5, msg='不要使用稀奇古怪的符合'))

        if zone_data and zone_data != '@':
            zone_data_check = zone_data.replace('-', '').replace('.', '')
            if not zone_data_check.isalnum():
                return self.write(dict(code=-6, msg='不要使用稀奇古怪的符合'))

        with DBContext('w', None, True) as session:
            if zone_type != 'NS':
                is_exist = session.query(DNSDomainZone).filter(DNSDomainZone.zone == zone,
                                                               DNSDomainZone.region == region,
                                                               DNSDomainZone.type == "NS",
                                                               DNSDomainZone.state == 'running').first()
                if not is_exist:
                    return self.write(dict(code=-5, msg='当前区域不存在NS记录，请添加'))

            mx = int(data.get('mx')) if data.get('mx') else None
            session.add(
                DNSDomainZone(zone=zone, host=host, type=zone_type, ttl=ttl, data=zone_data, region=region, mx=mx))

            nickname = self.get_current_nickname()
            log_msg = '添加记录： {} 记录 {} 区域/线路 {} 值{}  用户：{}'.format(zone_type, region, host, zone_data, nickname)
            session.add(DNSDomainLog(domain_name=zone, log_data=log_msg))

        return self.write(dict(code=0, msg='添加成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        zone_id = data.get('zone_id')
        zone = data.get('zone')
        host = data.get('host')
        zone_type = data.get('type')
        ttl = data.get('ttl')
        zone_data = data.get('data')
        region = data.get('region', 'any')

        if zone_type == 'NS':
            if not zone or not zone_type or not ttl or not zone_data or not region:
                return self.write(dict(code=-1, msg='必填参数不能为空'))
        else:
            if not zone or not host or not zone_type or not ttl or not zone_data or not region:
                return self.write(dict(code=-1, msg='必填参数不能为空'))

        if zone_type == 'MX':
            mx = data.get('mx')
            if not mx:
                return self.write(dict(code=-2, msg='请设置MX优先级'))

        if host and check_contain_chinese(host) or check_contain_chinese(zone_data):
            return self.write(dict(code=-2, msg='不支持汉字'))

        if zone_type == 'A':
            if not is_ip(zone_data):
                return self.write(dict(code=-3, msg='A记录值 必须为IP'))

        if zone_type == 'CNAME' or zone_type == 'NS':
            if zone_data[-1] == '.':
                zone_data_cname = zone_data[:-1]
            else:
                zone_data_cname = zone_data

            if not is_domain(zone_data_cname):
                if zone_type == 'NS':
                    return self.write(dict(code=-4, msg='NS记录值 必须为域名，且一定可访问，不然会导致整个区域不可用'))
                else:
                    return self.write(dict(code=-4, msg='CNAME记录值 必须为域名'))
            zone_data = zone_data_cname + '.'

        if host and host not in ['@', '*']:
            if host == '.':
                return self.write(dict(code=-5, msg='请使用合法的记录'))
            if host[0] in ['-', '.'] or host[-1] in ['-', '.']:
                return self.write(dict(code=-5, msg='不合法记录'))

            host_check = host.replace('-', '').replace('.', '')
            if not host_check:
                return self.write(dict(code=-5, msg='不合法记录'))

            if not host_check.isalnum():
                return self.write(dict(code=-5, msg='不要使用稀奇古怪的符合'))

        if zone_data and zone_data != '@':
            zone_data_check = zone_data.replace('-', '').replace('.', '')
            if not zone_data_check.isalnum():
                return self.write(dict(code=-6, msg='不要使用稀奇古怪的符合'))

        with DBContext('w', None, True) as session:
            if zone_type != 'NS':
                is_exist = session.query(DNSDomainZone).filter(DNSDomainZone.zone == zone,
                                                               DNSDomainZone.region == region,
                                                               DNSDomainZone.type == "NS",
                                                               DNSDomainZone.state == 'running').first()
                if not is_exist:
                    return self.write(dict(code=-5, msg='当前区域不存在NS记录，请添加'))

            zone_info = session.query(DNSDomainZone).filter(DNSDomainZone.zone_id == zone_id).first()

            mx = int(data.get('mx')) if data.get('mx') else None
            session.query(DNSDomainZone).filter(DNSDomainZone.zone_id == zone_id).update(
                {DNSDomainZone.zone: zone, DNSDomainZone.host: host, DNSDomainZone.type: zone_type,
                 DNSDomainZone.ttl: ttl, DNSDomainZone.data: zone_data, DNSDomainZone.region: region,
                 DNSDomainZone.mx: mx})

            nickname = self.get_current_nickname()
            log_msg = '修改记录： 用户：{}，记录 {} > {}，类型：{} > {}，值：{} > {}，区域：{} > {}。'.format(nickname, host,
                                                                                       zone_info.host,
                                                                                       zone_type, zone_info.type,
                                                                                       zone_data, zone_info.data,
                                                                                       region, zone_info.region)
            session.add(DNSDomainLog(domain_name=zone, log_data=log_msg))

        return self.write(dict(code=0, msg='修改成功'))

    def patch(self, *args, **kwargs):
        # 启用 暂停
        data = json.loads(self.request.body.decode("utf-8"))
        zone_id = data.get('zone_id')
        id_list = data.get('id_list')
        state = data.get('state')

        if state == 'running':
            state = 'stop'
        elif state == 'stop':
            state = 'running'
        else:
            return self.write(dict(code=-1, msg='意料之外的参数'))

        with DBContext('w', None, True) as session:
            if zone_id:
                session.query(DNSDomainZone).filter(DNSDomainZone.zone_id == zone_id).update(
                    {DNSDomainZone.state: state})
                ### log
                zone_info = session.query(DNSDomainZone).filter(DNSDomainZone.zone_id == zone_id).first()
                nickname = self.get_current_nickname()
                log_msg = '禁用/启用记录： {} 记录 {} 区域/线路 {} 值{}  用户：{}'.format(zone_info.type, zone_info.region,
                                                                         zone_info.host, zone_info.data, nickname)
                session.add(DNSDomainLog(domain_name=zone_info.zone, log_data=log_msg))
            elif id_list:
                for i in id_list:
                    session.query(DNSDomainZone).filter(DNSDomainZone.zone_id == i).update(
                        {DNSDomainZone.state: state})
                    ### log
                    zone_info = session.query(DNSDomainZone).filter(DNSDomainZone.zone_id == i).first()
                    nickname = self.get_current_nickname()
                    log_msg = '禁用/启用记录： {} 记录 {} 区域/线路 {} 值{}  用户：{}'.format(zone_info.type, zone_info.region,
                                                                             zone_info.host, zone_info.data, nickname)
                    session.add(DNSDomainLog(domain_name=zone_info.zone, log_data=log_msg))
            else:
                return self.write(dict(code=1, msg='关键参数不能为空'))
        self.write(dict(code=0, msg='成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        zone_id = data.get('zone_id')
        id_list = data.get('id_list')

        with DBContext('w', None, True) as session:
            if zone_id:
                ### log
                zone_info = session.query(DNSDomainZone).filter(DNSDomainZone.zone_id == zone_id).first()
                nickname = self.get_current_nickname()
                log_msg = '删除记录： {} 记录 {} 区域/线路 {} 值{}  用户：{}'.format(zone_info.type, zone_info.region,
                                                                      zone_info.host, zone_info.data, nickname)
                session.add(DNSDomainLog(domain_name=zone_info.zone, log_data=log_msg))
                session.query(DNSDomainZone).filter(DNSDomainZone.zone_id == zone_id).delete(synchronize_session=False)
            elif id_list:
                for i in id_list:
                    i = int(i)
                    ### log
                    zone_info = session.query(DNSDomainZone).filter(DNSDomainZone.zone_id == i).first()
                    nickname = self.get_current_nickname()
                    log_msg = '删除记录： {} 记录 {} 区域/线路 {} 值{}  用户：{}'.format(zone_info.type, zone_info.region,
                                                                          zone_info.host, zone_info.data, nickname)
                    session.add(DNSDomainLog(domain_name=zone_info.zone, log_data=log_msg))
                    session.query(DNSDomainZone).filter(DNSDomainZone.zone_id == i).delete(synchronize_session=False)
            else:
                return self.write(dict(code=1, msg='关键参数不能为空'))

        self.write(dict(code=0, msg='删除成功'))


class DomainNameV2(BaseHandler):
    def get(self, *args, **kwargs):
        domain_list = []
        with DBContext('r') as session:
            domain_info = session.query(DNSDomainName.domain_name).filter(
                DNSDomainName.domain_state == 'running').all()

        for msg in domain_info:
            domain_list.append(msg[0])

        self.write(dict(code=0, msg='获取成功', data=domain_list))


class DomainZoneV2(BaseHandler):
    def get(self, *args, **kwargs):
        domain = self.get_argument('domain', default=None, strip=True)
        zone_list = []
        if not domain:
            return self.write(dict(code=-1, msg='请选择一个域名'))

        with DBContext('r') as session:
            zone_info = session.query(DNSDomainZone).filter(DNSDomainZone.zone == domain).order_by(
                DNSDomainZone.region, DNSDomainZone.zone_id).all()
        for msg in zone_info:
            data_dict = model_to_dict(msg)
            data_dict.pop('update_time')
            zone_list.append(data_dict)
        self.write(dict(code=0, msg='获取成功', data=zone_list))


class DomainConfHandler(BaseHandler):
    def get(self, *args, **kwargs):
        new_dict = {}
        with DBContext('r') as session:
            conf_info = session.query(DNSDomainConf).all()

        for msg in conf_info:
            data_dict = model_to_dict(msg)
            new_dict[data_dict.get('conf_name')] = data_dict.get('conf_value')

        self.write(dict(code=0, msg='获取成功', data=new_dict))


class DomainLogHandler(BaseHandler):
    def get(self, *args, **kwargs):
        domain = self.get_argument('domain', default=None, strip=True)
        log_list = []
        if not domain:
            return self.write(dict(code=-1, msg='域名参数不能为空'))
        with DBContext('r') as session:
            domain_log = session.query(DNSDomainLog).filter(DNSDomainLog.domain_name == domain).order_by(
                -DNSDomainLog.id).all()

        for msg in domain_log:
            data_dict = model_to_dict(msg)
            data_dict['update_time'] = str(data_dict['update_time'])
            log_list.append(data_dict)
        self.write(dict(code=0, msg='获取成功', data=log_list))


domain_urls = [
    (r"/v1/dns/bind/domain/", DomainName),
    (r"/v2/dns/bind/domain/", DomainNameV2),
    (r"/v1/dns/bind/zone/", DomainZone),
    (r"/v2/dns/bind/zone/", DomainZoneV2),
    (r"/v1/dns/bind/conf/", DomainConfHandler),
    (r"/v1/dns/bind/log/", DomainLogHandler),
    (r"/are_you_ok/", LivenessProbe),
]
