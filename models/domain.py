#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019年5月7日
Desc    : 数据库ORM
"""

from sqlalchemy import Column, String, Integer, DateTime, Text
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
    domain_name = Column('domain_name', String(255) ,unique=True ,nullable=False)
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
    log_data= Column('log_data', Text())
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)

