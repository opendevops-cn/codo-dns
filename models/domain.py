#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019年5月7日
Desc    : 数据库ORM
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import class_mapper
from datetime import datetime

Base = declarative_base()


def model_to_dict(model):
    model_dict = {}
    for key, column in class_mapper(model.__class__).c.items():
        model_dict[column.name] = getattr(model, key, None)
    return model_dict


class DNSDomainName(Base):
    __tablename__ = 'dns_domain_name'

    domain_id = Column('domain_id', Integer, primary_key=True, autoincrement=True)
    domain_name = Column('domain_name', String(255), unique=True, nullable=False)
    domain_code = Column('domain_code', String(80))
    domain_state = Column('domain_state', String(10), default='running')
    create_time = Column('create_time', DateTime(), default=datetime.now)


class DNSDomainZone(Base):
    __tablename__ = 'dns_domain_zone'

    ###
    zone_id = Column('zone_id', Integer, primary_key=True, autoincrement=True)
    zone = Column('zone', String(255))
    region = Column('region', String(100))
    host = Column('host', String(255))
    type = Column('type', String(8))
    ttl = Column('ttl', Integer)
    data = Column('data', String(255))
    mx = Column('mx', Integer)
    state = Column('state', String(10), default='running')
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)


class DNSDomainConf(Base):
    __tablename__ = 'dns_domain_conf'

    ### 配置
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    conf_name = Column('conf_name', String(100), nullable=False)
    conf_value = Column('conf_value', Text())
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)


class DNSDomainLog(Base):
    __tablename__ = 'dns_domain_log'

    ### 日志
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    domain_name = Column('domain_name', String(255))
    log_data = Column('log_data', Text())
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)


####
class DomainCloudConf(Base):
    __tablename__ = 'cloud_domain_account'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    alias_name = Column('alias_name', String(80), index=True, unique=True, nullable=False)
    cloud_name = Column('cloud_name', String(80), nullable=False)
    cloud_code = Column('cloud_code', String(80), nullable=False)
    access_id = Column('access_id', String(128))
    access_key = Column('access_key', String(250))
    state = Column('state', Boolean(), default=True)
    create_time = Column('create_time', DateTime(), default=datetime.now)


class DomainName(Base):
    __tablename__ = 'cloud_domain_name'
    id = Column('id', Integer, primary_key=True, autoincrement=True)

    domain_id = Column('domain_id', String(128), index=True, unique=True, nullable=False)
    account = Column('account', String(128), index=True)
    cloud_name = Column('cloud_name', String(80), nullable=False, default='unknown')

    domain_name = Column('domain_name', String(128), index=True, unique=True, nullable=False)
    record_count = Column('record_count', String(80), index=True, default=0)
    domain_state = Column('domain_state', String(20), default='running')
    remark = Column('remark', String(80), default='unknown')
    star_mark = Column('star_mark', Boolean(), index=True, default=False)  ### 标星
    record_end_time = Column('record_end_time', DateTime(), default=datetime.now)
    create_time = Column('create_time', DateTime(), default=datetime.now)
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)

    __mapper_args__ = {
        "order_by": -star_mark
    }


class DomainRecords(Base):
    __tablename__ = 'cloud_domain_records'
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    domain_name = Column('domain_name', String(128), index=True, nullable=False)
    account = Column('account', String(80), index=True)
    record_id = Column('record_id', String(128), index=True, unique=True)  ### 解析记录ID
    domain_rr = Column('domain_rr', String(128), index=True, default='www')  ### 主机记录。
    domain_type = Column('domain_type', String(20), default='A')  ###记录类型
    domain_value = Column('domain_value', String(250), default='')  ###记录值。
    domain_ttl = Column('domain_ttl', Integer, default=600)  ###生存时间
    domain_mx = Column('domain_mx', Integer, default=5)  ###MX记录的优先级。
    line = Column('line', String(50), default='default')  ## 解析线路  默认/境外
    state = Column('state', String(50), default='default')  ## 当前的解析记录状态
    remark = Column('remark', String(80), default='unknown')  ### 备注

    update_user = Column('update_user', String(50), default='unknown')  ### 最后修改人
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)


class DomainOptLog(Base):
    __tablename__ = 'cloud_domain_opt_log'

    ### 日志
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    domain_name = Column('domain_name', String(128), index=True, nullable=False)
    username = Column('username', String(50))  ### 执行人
    action = Column('action', String(20))  ##操作方法
    record = Column('record', Text())  ## 记录
    state = Column('状态', String(50), default='error')
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)


class DomainSyncLog(Base):
    __tablename__ = 'cloud_domain_sync_log'

    ### 日志
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    present = Column('present', String(50), default='unknown')
    alias_name = Column('别名', String(128), default='unknown')
    access_id = Column('access_id', String(128), default='unknown')
    record = Column('record', Text())  ## 记录
    state = Column('状态', String(20), default='错误')
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)


class DomainCheckSSL(Base):
    __tablename__ = 'domain_check_ssl'
    id = Column('id', Integer, primary_key=True, autoincrement=True)

    domain_name = Column('domain_name', String(128), index=True, unique=True, nullable=False)
    record = Column('record', Text())  ## 记录
    port_list = Column('port', Text())
    is_valid = Column('是否启用', String(50), index=True, default='yes')
    update_user = Column('最后修改人', String(50), default='unknown')  ### 最后修改人
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)
