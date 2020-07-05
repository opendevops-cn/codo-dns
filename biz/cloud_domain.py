#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019年5月7日
Desc    : 云解析DNS记录
"""

import time
import datetime
from shortuuid import uuid
from websdk.consts import const
from websdk.configs import configs
from websdk.model_utils import queryset_to_list
from websdk.db_context import DBContext
from models.domain import DomainCloudConf, DomainName, DomainRecords, DomainSyncLog
from websdk.tools import RedisLock
from libs.qcloud_domain import QCloud
from libs.dnspod_domain import DNSPod
from libs.godaddy_domain import GoDaddy
from libs.aliyun_domain import AliYun

"""
aliyun-python-sdk-dysmsap===1.0.0
dnspod-python===1.0.0
GoDaddyPy===2.3.3
"""


def deco(cls, release=False):
    def _deco(func):
        def __deco(*args, **kwargs):
            if not cls.get_lock(cls, key_timeout=600, func_timeout=60): return False
            try:
                return func(*args, **kwargs)
            finally:
                ### 执行完就释放key，默认不释放
                if release: cls.release(cls)

        return __deco

    return _deco


def domain_factory(cloud, **kwargs):
    if cloud in ['阿里云', 'aliyun', 'AliYun']:
        return AliYun(**kwargs)

    elif cloud in ['腾讯云', 'qcloud', 'QCloud']:
        return QCloud(**kwargs)

    elif cloud in ['DNSPod', 'dnspod']:
        return DNSPod(**kwargs)

    elif cloud in ['GoDaddy', 'godaddy']:
        return GoDaddy(**kwargs)
    else:
        return None


def all_sync_index():
    __redis_info = configs.get(const.REDIS_CONFIG_ITEM, None).get(const.DEFAULT_RD_KEY, None)

    @deco(RedisLock("domain_sync_redis_lock_key", **dict(host=__redis_info.get(const.RD_HOST_KEY),
                                                         port=__redis_info.get(const.RD_PORT_KEY, 6379),
                                                         db=__redis_info.get(const.RD_DB_KEY, 0),
                                                         password=__redis_info.get(const.RD_PASSWORD_KEY, None))))
    def index():
        domain_main('阿里云')
        domain_main('腾讯云')
        domain_main('DNSPod')
        domain_main('GoDaddy')

    index()


def domain_main(cloud_name):
    with DBContext('r') as session:
        config_info = session.query(DomainCloudConf).filter(DomainCloudConf.cloud_name == cloud_name).all()
        the_configs = queryset_to_list(config_info)

    for config in the_configs:
        access_id, alias_name = config.get('access_id'), config.get('alias_name')
        ### 十天没有更新则改状态为过期 过期十天则删除
        old_date = datetime.datetime.now() - datetime.timedelta(days=10)
        old_date1 = datetime.datetime.now() - datetime.timedelta(hours=2)
        start_time = time.time()
        with DBContext('w', None, True) as session:
            if cloud_name in ['GoDaddy', 'godaddy']:
                session.query(DomainName).filter(DomainName.account == alias_name, DomainName.domain_state != 'disable',
                                                 DomainName.update_time < old_date).update(
                    {DomainName.domain_state: "过期"})
                session.query(DomainName).filter(DomainName.account == alias_name, DomainName.domain_state != 'disable',
                                                 DomainName.update_time < old_date1).update(
                    {DomainName.domain_state: "未知"})
            else:
                session.query(DomainName).filter(DomainName.account == alias_name,
                                                 DomainName.update_time < old_date).update(
                    {DomainName.domain_state: "过期"})
                session.query(DomainName).filter(DomainName.account == alias_name,
                                                 DomainName.update_time < old_date1).update(
                    {DomainName.domain_state: "未知"})

            session.query(DomainName).filter(DomainName.account == alias_name, DomainName.domain_state == "过期",
                                             DomainName.update_time < old_date).delete(synchronize_session=False)
            ###
            session.add(DomainSyncLog(present='{} DNS'.format(cloud_name), alias_name=alias_name,
                                      access_id=access_id, state="正常", record='开始同步'))

        obj = domain_factory(cloud_name, **config)
        try:
            domain_list = obj.describe_domains()
            if not domain_list: return
            for domain in domain_list:
                data_sync_domain(cloud_name, access_id, alias_name, domain)
                record_list = obj.record_generator(**domain)
                data_sync_record(cloud_name, access_id, alias_name, record_list)

        except Exception as err:
            with DBContext('w', None, True) as session:
                session.add(DomainSyncLog(present='{} DNS'.format(cloud_name), alias_name=alias_name,
                                          access_id=access_id, state="错误", record=str(err)))

        with DBContext('w', None, True) as session:
            duration = time.time() - start_time
            session.add(DomainSyncLog(present='{} DNS'.format(cloud_name), alias_name=alias_name,
                                      access_id=access_id, state="正常", record='同步结束，耗时： %.3f s' % duration))


def data_sync_domain(cloud_name, access_id, alias_name, domain):
    with DBContext('w', None, True) as session:
        if cloud_name == "阿里云":
            domain_name = domain.get('DomainName')
            domain_id = domain.get('DomainId')
            is_exist = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()
            state = '过期' if domain.get('InstanceExpired', False) else '正常'
            if is_exist:
                session.query(DomainName).filter(DomainName.domain_name == domain_name).update(
                    {DomainName.domain_id: domain_id, DomainName.record_count: domain.get('RecordCount'),
                     DomainName.domain_state: state, DomainName.account: alias_name,
                     DomainName.cloud_name: cloud_name})
            else:
                new_domain = DomainName(domain_name=domain_name, domain_id=domain_id,
                                        record_count=domain.get('RecordCount'), domain_state=state,
                                        account=alias_name, cloud_name=cloud_name)
                session.add(new_domain)
        elif cloud_name == "腾讯云":
            domain_name = domain.get('name')
            domain_id = domain.get('id')

            if domain.get('ext_status') == 'notexist':
                state = '未注册'
            elif domain.get('ext_status') == 'dnserror':
                state = '错误'
            elif domain.get('ext_status') == '':
                state = '正常'
            else:
                state = '未知'

            if session.query(DomainName).filter(DomainName.domain_name == domain_name).first():
                session.query(DomainName).filter(DomainName.domain_name == domain_name).update(
                    {DomainName.domain_id: domain_id, DomainName.record_count: domain.get('records'),
                     DomainName.domain_state: state, DomainName.account: alias_name,
                     DomainName.cloud_name: cloud_name})
            else:
                new_domain = DomainName(domain_name=domain_name, domain_id=domain_id,
                                        record_count=domain.get('records'), domain_state=state,
                                        account=alias_name, cloud_name=cloud_name)
                session.add(new_domain)
        elif cloud_name == "DNSPod":
            domain_id, domain_name = domain.get('id'), domain.get('name')

            if domain.get('ext_status') == 'notexist':
                state = '未注册'
            elif domain.get('ext_status') == 'dnserror':
                state = '错误'
            elif domain.get('ext_status') == '':
                state = '正常'
            else:
                state = '未知'

            if session.query(DomainName).filter(DomainName.domain_name == domain_name).first():
                session.query(DomainName).filter(DomainName.domain_name == domain_name).update(
                    {DomainName.domain_id: domain_id, DomainName.record_count: domain.get('records'),
                     DomainName.domain_state: state, DomainName.account: alias_name,
                     DomainName.cloud_name: cloud_name})
            else:
                new_domain = DomainName(domain_name=domain_name, domain_id=domain_id,
                                        record_count=domain.get('records'), domain_state=state,
                                        account=alias_name, cloud_name=cloud_name)
                session.add(new_domain)

        elif cloud_name == "GoDaddy":
            domain_name = domain.get('domain')
            domain_id = domain.get('domainId')

            if domain.get('status') in ['ACTIVE', 'OK']:
                state = '正常'
            else:
                state = '错误'

            if session.query(DomainName).filter(DomainName.domain_name == domain_name).first():
                session.query(DomainName).filter(DomainName.domain_name == domain_name).update(
                    {DomainName.domain_id: domain_id, DomainName.record_count: domain.get('records'),
                     DomainName.domain_state: state, DomainName.account: alias_name,
                     DomainName.cloud_name: cloud_name})
            else:
                new_domain = DomainName(domain_name=domain_name, domain_id=domain_id,
                                        record_count=domain.get('records'), domain_state=state,
                                        account=alias_name, cloud_name=cloud_name)
                session.add(new_domain)
        else:
            pass


def data_sync_record(cloud_name, access_id, alias_name, record_list):
    with DBContext('w', None, True) as session:
        for record_info in record_list:
            domain_name = record_info.get('domain_name')
            record = record_info.get('data_dict')
            if cloud_name == '阿里云':
                record_id = record.get('RecordId')
                record_ex = session.query(DomainRecords).filter(DomainRecords.record_id == record_id).first()
                if record_ex:
                    session.query(DomainRecords).filter(DomainRecords.domain_name == domain_name,
                                                        DomainRecords.record_id == record_id).update(
                        {DomainRecords.domain_rr: record.get('RR', ''),
                         DomainRecords.domain_type: record.get('Type', ''),
                         DomainRecords.domain_value: record.get('Value', ''),
                         DomainRecords.domain_ttl: int(record.get('TTL', 600)),
                         DomainRecords.domain_mx: record.get('Weight', 0),
                         DomainRecords.line: record.get('Line', ''),
                         DomainRecords.state: record.get('Status', ''),
                         DomainRecords.remark: record.get('Remark', 'unknown'),
                         DomainRecords.account: alias_name})
                else:
                    new_record = DomainRecords(domain_name=domain_name,
                                               record_id=record_id,
                                               domain_rr=record.get('RR', ''),
                                               domain_type=record.get('Type', ''),
                                               domain_value=record.get('Value', ''),
                                               domain_ttl=int(record.get('TTL', 600)),
                                               domain_mx=int(record.get('Weight', 0)),
                                               line=record.get('Line', 'unknown'),
                                               state=record.get('Status', 'unknown'),
                                               remark=record.get('Remark', 'unknown'),
                                               account=alias_name)
                    session.add(new_record)
            elif cloud_name == '腾讯云':
                record_id = record.get('id')
                state = 'disable' if record.get('enabled') == 0 else 'enable'  ##1和0分别代表启用和暂停
                record_ex = session.query(DomainRecords).filter(DomainRecords.record_id == record_id).first()

                if record_ex:
                    session.query(DomainRecords).filter(DomainRecords.domain_name == domain_name,
                                                        DomainRecords.record_id == record_id).update(
                        {DomainRecords.domain_rr: record.get('name', ''),
                         DomainRecords.domain_type: record.get('type', ''),
                         DomainRecords.domain_value: record.get('value', ''),
                         DomainRecords.domain_ttl: int(record.get('ttl', 600)),
                         DomainRecords.domain_mx: record.get('mx', 0),
                         DomainRecords.line: record.get('line', ''),
                         DomainRecords.state: state,
                         DomainRecords.account: alias_name})
                else:
                    new_record = DomainRecords(domain_name=domain_name,
                                               record_id=record_id,
                                               domain_rr=record.get('name', ''),
                                               domain_type=record.get('type', ''),
                                               domain_value=record.get('value', ''),
                                               domain_ttl=int(record.get('ttl', 600)),
                                               domain_mx=int(record.get('mx', 0)),
                                               line=record.get('line', 'unknown'),
                                               state=state,
                                               account=alias_name)
                    session.add(new_record)
            elif cloud_name == 'DNSPod':
                record_id = record.get('id')
                state = 'disable' if record.get('enabled') == 0 else 'enable'  ##1和0分别代表启用和暂停
                record_ex = session.query(DomainRecords).filter(DomainRecords.record_id == record_id).first()

                if record_ex:
                    session.query(DomainRecords).filter(DomainRecords.domain_name == domain_name,
                                                        DomainRecords.record_id == record_id).update(
                        {DomainRecords.domain_rr: record.get('name', ''),
                         DomainRecords.domain_type: record.get('type', ''),
                         DomainRecords.domain_value: record.get('value', ''),
                         DomainRecords.domain_ttl: int(record.get('ttl', 600)),
                         DomainRecords.domain_mx: record.get('mx', 0),
                         DomainRecords.line: record.get('line', ''),
                         DomainRecords.state: state,
                         DomainRecords.account: alias_name})
                else:
                    new_record = DomainRecords(domain_name=domain_name,
                                               record_id=record_id,
                                               domain_rr=record.get('name', ''),
                                               domain_type=record.get('type', ''),
                                               domain_value=record.get('value', ''),
                                               domain_ttl=int(record.get('ttl', 600)),
                                               domain_mx=int(record.get('mx', 0)),
                                               line=record.get('line', 'unknown'),
                                               state=state,
                                               account=alias_name)
                    session.add(new_record)
            elif cloud_name == 'GoDaddy':
                record_ex = session.query(DomainRecords).filter(DomainRecords.domain_rr == record.get('name'),
                                                                DomainRecords.domain_type == record.get('type'),
                                                                DomainRecords.domain_value == record.get('data'),
                                                                DomainRecords.account == alias_name,
                                                                DomainRecords.domain_name == domain_name).first()

                if record_ex:
                    session.query(DomainRecords).filter(DomainRecords.domain_rr == record.get('name'),
                                                        DomainRecords.domain_type == record.get('type'),
                                                        DomainRecords.domain_value == record.get('data'),
                                                        DomainRecords.account == alias_name,
                                                        DomainRecords.domain_name == domain_name).update({
                        DomainRecords.domain_rr: record.get('name', ''),
                        DomainRecords.domain_type: record.get('type', ''),
                        DomainRecords.domain_value: record.get('data', ''),
                        DomainRecords.domain_ttl: int(record.get('ttl', 600)),
                        DomainRecords.domain_mx: record.get('mx', 0),
                        DomainRecords.line: record.get('line', 'default'),
                        DomainRecords.state: record.get('status', 'ENABLE'),
                        DomainRecords.account: alias_name})
                else:
                    new_record = DomainRecords(domain_name=domain_name,
                                               record_id=str(uuid()),
                                               domain_rr=record.get('name', ''),
                                               domain_type=record.get('type', ''),
                                               domain_value=record.get('data', ''),
                                               domain_ttl=int(record.get('ttl', 600)),
                                               domain_mx=int(record.get('mx', 0)),
                                               line=record.get('line', 'default'),
                                               state=record.get('status', 'ENABLE'),
                                               account=alias_name)
                    session.add(new_record)
