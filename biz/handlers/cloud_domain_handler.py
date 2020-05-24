#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/5/6
"""

import json
import datetime
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from tornado import gen
from sqlalchemy import or_
from libs.base_handler import BaseHandler
from biz.cloud_domain import domain_factory, domain_main
from websdk.model_utils import model_to_dict, queryset_to_list
from websdk.db_context import DBContext
from models.domain import DomainName, DomainRecords, DomainCloudConf, DomainOptLog


class CloudDomainHandler(BaseHandler):
    def get(self, *args, **kwargs):
        search_v = self.get_argument('search_value', default=None, strip=True)
        with DBContext('r') as session:
            if search_v:
                domain_info = session.query(DomainName).filter(or_(DomainName.domain_name.like('{}%'.format(search_v)),
                                                                   DomainName.cloud_name.like('{}%'.format(search_v)),
                                                                   DomainName.account.like(
                                                                       '{}%'.format(search_v)))).all()
            else:
                domain_info = session.query(DomainName).all()
        domain_list = queryset_to_list(domain_info)
        self.write(dict(code=0, msg='获取成功', data=domain_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        domain_name = data.get('domain_name')
        remark = data.get('remark')
        record_end_time = data.get('record_end_time')
        state = data.get('state')
        if not domain_name or not record_end_time:  return self.write(dict(code=-1, msg='关键参数不能为空'))

        end_time = datetime.datetime.strptime(record_end_time, "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)

        with DBContext('w', None, True) as session:
            is_exist = session.query(DomainName.domain_id).filter(DomainName.domain_name == domain_name).first()

            if is_exist: return self.write(dict(code=-2, msg='当前域名已经存在'))
            session.add(DomainName(domain_id=domain_name, domain_name=domain_name, remark=remark,
                                   record_end_time=end_time, domain_state=state, cloud_name='unknown'))

        self.write(dict(code=0, msg='添加成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        the_id = data.get('id')
        remark = data.get('remark')
        record_end_time = data.get('record_end_time')
        if not the_id or not record_end_time:  return self.write(dict(code=-1, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            session.query(DomainName).filter(DomainName.id == int(the_id)).update({DomainName.remark: remark,
                                                                                   DomainName.record_end_time: record_end_time})

        return self.write(dict(code=0, msg='修改完成'))

    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        star_mark = data.get('star_mark')
        the_id = data.get('id')
        if not isinstance(star_mark, bool): return self.write(dict(code=-1, msg='星标数据有误'))
        if not the_id: return self.write(dict(code=-2, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            session.query(DomainName).filter(DomainName.id == int(the_id)).update({DomainName.star_mark: star_mark})
        return self.write(dict(code=0, msg='星标成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        select_list = data.get('select_list')
        if not select_list: return self.write(dict(code=1, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            for i in select_list:
                i = int(i)
                domain_info = session.query(DomainName).filter(DomainName.id == i).first()
                session.add(DomainOptLog(domain_name=domain_info.domain_name, username=self.request_username,
                                         action='删除', record='删除根域名'))
                session.query(DomainName).filter(DomainName.id == i).delete(synchronize_session=False)

        self.write(dict(code=0, msg='删除成功'))


class CloudRecordHandler(BaseHandler):
    _thread_pool = ThreadPoolExecutor(5)

    def get(self, *args, **kwargs):
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=1000, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)

        search_v = self.get_argument('search_value', default=None, strip=True)
        domain_name = self.get_argument('domain_name', default=None, strip=True)

        if not domain_name: return self.write(dict(code=0, msg='关键参数域名不能为空'))

        with DBContext('r') as session:
            if search_v:
                the_count = session.query(DomainRecords).filter(DomainRecords.domain_name == domain_name,
                                                                or_(DomainRecords.domain_rr.like(
                                                                    '{}%'.format(search_v)),
                                                                    DomainRecords.domain_type.like(
                                                                        '{}%'.format(search_v)),
                                                                    DomainRecords.line.like('{}%'.format(search_v)),
                                                                    DomainRecords.record_id.like(
                                                                        '{}%'.format(search_v)),
                                                                    DomainRecords.state.like('{}%'.format(search_v)),
                                                                    DomainRecords.account.like(
                                                                        '{}%'.format(search_v)),
                                                                    DomainRecords.domain_value.like(
                                                                        '{}%'.format(search_v)))).count()

                record_info = session.query(DomainRecords).filter(DomainRecords.domain_name == domain_name,
                                                                  or_(DomainRecords.domain_rr.like(
                                                                      '{}%'.format(search_v)),
                                                                      DomainRecords.domain_type.like(
                                                                          '{}%'.format(search_v)),
                                                                      DomainRecords.line.like('{}%'.format(search_v)),
                                                                      DomainRecords.record_id.like(
                                                                          '{}%'.format(search_v)),
                                                                      DomainRecords.state.like('{}%'.format(search_v)),
                                                                      DomainRecords.account.like(
                                                                          '{}%'.format(search_v)),
                                                                      DomainRecords.domain_value.like(
                                                                          '{}%'.format(search_v)))).offset(
                    limit_start).limit(int(limit))
            else:
                the_count = session.query(DomainRecords).filter(DomainRecords.domain_name == domain_name).count()
                record_info = session.query(DomainRecords).filter(DomainRecords.domain_name == domain_name).offset(
                    limit_start).limit(int(limit))

        record_list = queryset_to_list(record_info)
        self.write(dict(code=0, msg='获取成功', data=record_list, count=the_count))

    @run_on_executor(executor='_thread_pool')
    def domain_post(self, domain, **base_new_dict):
        return domain.add_record(**base_new_dict)

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        domain_name = data.get('domain_name')
        with DBContext('r') as session:
            domain_obj = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()
            account_obj = session.query(DomainCloudConf).filter(
                DomainCloudConf.alias_name == domain_obj.account).first()

        base_new_dict = dict(
            domain_name=domain_name,
            domain_rr=data.get('domain_rr'),
            domain_type=data.get('domain_type'),
            domain_value=data.get('domain_value'),
            domain_ttl=int(data.get('domain_ttl')),
            domain_mx=int(data.get('domain_mx', 0)),
            line=data.get('line'),
        )
        try:
            domain = domain_factory(account_obj.cloud_name, domain_id=domain_obj.domain_id,
                                    access_id=account_obj.access_id,
                                    access_key=account_obj.access_key, domain_name=domain_name)
            result_data = yield self.domain_post(domain, **base_new_dict)

        except Exception as err:
            log_data = dict(
                domain_name=domain_name,
                username=self.request_username,
                action="API",
                record='账号别名：{}， 错误信息：{}'.format(account_obj.alias_name, str(err)),
                state="失败"
            )
            with DBContext('w', None, True) as session:
                session.add(DomainOptLog(**log_data))
            return self.write(dict(code=-1, msg='添加失败，详情请看日志'))
        if result_data:
            log_state = "成功"
            new_dict = {**base_new_dict, **dict(
                account=account_obj.alias_name,
                record_id=result_data
            )}
            with DBContext('w', None, True) as session:
                session.add(DomainRecords(**new_dict))

        else:
            log_state = "失败"

        log_data = dict(
            domain_name=domain_name,
            username=self.request_username,
            action="添加",
            record='类型：{}， {}， 线路：{}， 记录：{}， (TTL：{})'.format(data.get('domain_type'),
                                                              data.get('domain_rr'),
                                                              data.get('line'), data.get('domain_value'),
                                                              data.get('domain_ttl')),
            state=log_state
        )
        with DBContext('w', None, True) as session:
            session.add(DomainOptLog(**log_data))

        if not result_data:  return self.write(dict(code=-1, msg='添加失败，详情请看日志'))
        return self.write(dict(code=0, msg='添加成功，详细变更信息请看日志'))

    @run_on_executor(executor='_thread_pool')
    def domain_put(self, domain, **base_new_dict):
        return domain.update_record(**base_new_dict)

    @gen.coroutine
    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        the_id = data.get('id')
        if not the_id: return self.write(dict(code=1, msg='关键参数不能为空'))

        with DBContext('r') as session:
            record_obj = session.query(DomainRecords).filter(DomainRecords.id == int(the_id)).first()
            domain_name = record_obj.domain_name
            account_obj = session.query(DomainCloudConf).filter(
                DomainCloudConf.alias_name == record_obj.account).first()
            domain_obj = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()

        if account_obj.cloud_name in ['GoDaddy', 'godaddy']:
            return self.write(dict(code=3, msg='GoDaddy 接口有BUG，暂时不支持修改'))
        base_new_dict = dict(
            record_id=record_obj.record_id,
            domain_name=domain_name,
            domain_rr=data.get('domain_rr'),
            domain_type=data.get('domain_type'),
            domain_value=data.get('domain_value'),
            domain_ttl=int(data.get('domain_ttl')),
            domain_mx=int(data.get('domain_mx', 0)),
            line=data.get('line'),
        )
        log_data = dict(
            domain_name=record_obj.domain_name,
            username=self.request_nickname,
            action="修改前",
            record='类型：{}， {}， 线路：{}， 记录：{}， (TTL：{})'.format(record_obj.domain_type, record_obj.domain_rr,
                                                              record_obj.line, record_obj.domain_value,
                                                              record_obj.domain_ttl),
            state="成功"
        )
        with DBContext('w', None, True) as session:
            session.add(DomainOptLog(**log_data))

            try:
                domain = domain_factory(account_obj.cloud_name, domain_id=domain_obj.domain_id,
                                        access_id=account_obj.access_id, access_key=account_obj.access_key,
                                        domain_name=domain_name)
                result_data = yield self.domain_put(domain, **base_new_dict)


            except Exception as err:
                log_data = dict(
                    domain_name=record_obj.domain_name,
                    username=self.request_nickname,
                    action="API",
                    record='账号别名：{}， 错误信息：{}'.format(account_obj.alias_name, str(err)),
                    state="失败"
                )
                session.add(DomainOptLog(**log_data))
                return self.write(dict(code=-1, msg='删除失败，详情请看日志'))

            if result_data:
                log_state = "成功"
                session.query(DomainRecords).filter(DomainRecords.id == int(the_id)).update(
                    {'record_id': record_obj.record_id, 'domain_rr': data.get('domain_rr'), 'line': data.get('line'),
                     'domain_type': data.get('domain_type'), 'domain_value': data.get('domain_value'),
                     'domain_ttl': data.get('domain_ttl'), 'domain_mx': int(data.get('domain_mx', 0))})
            else:
                log_state = "失败"
                ### 记录变更日志
            log_data = dict(
                domain_name=record_obj.domain_name,
                username=self.request_nickname,
                action="修改后",
                record='类型：{}， {}， 线路：{}， 记录：{}， (TTL：{})'.format(data.get('domain_type'),
                                                                  data.get('domain_rr'), data.get('line'),
                                                                  data.get('domain_value'), data.get('domain_ttl')),
                state=log_state
            )
            session.add(DomainOptLog(**log_data))
            if not result_data: return self.write(dict(code=-2, msg='修改失败，详情请看日志'))

        return self.write(dict(code=0, msg='修改完成'))

    @run_on_executor(executor='_thread_pool')
    def domain_patch(self, domain, **base_new_dict):
        return domain.set_record_status(**base_new_dict)

    @gen.coroutine
    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        if data.get('action') == 'disable':
            action = "禁用"
        elif data.get('action') == 'enable':
            action = "启用"
        else:
            action = "参数有误"
        select_list = data.get('select_list')

        with DBContext('r') as session:
            select_record = session.query(DomainRecords).filter(DomainRecords.id.in_(select_list)).all()
            if select_record and len(select_record) > 0:
                record_obj = select_record[0]
                domain_name = record_obj.domain_name
                account_obj = session.query(DomainCloudConf).filter(
                    DomainCloudConf.alias_name == record_obj.account).first()
                domain_obj = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()
            else:
                return self.write(dict(code=-1, msg='参数有误'))

        if account_obj.cloud_name in ['GoDaddy', 'godaddy']:
            return self.write(dict(code=3, msg='GoDaddy 接口有BUG，暂时不支持禁用/启用'))

        domain_name = record_obj.domain_name
        domain = domain_factory(account_obj.cloud_name, domain_id=domain_obj.domain_id,
                                access_id=account_obj.access_id, access_key=account_obj.access_key,
                                domain_name=domain_name)
        with DBContext('w', None, True) as session:
            for r in select_record:
                ###
                base_new_dict = dict(
                    domain_name=domain_name,
                    record_id=r.record_id,
                    status=action,
                    ###
                    domain_rr=r.domain_rr,
                    domain_type=r.domain_type,
                    domain_value=r.domain_value,
                    domain_ttl=int(r.domain_ttl),
                    domain_mx=int(r.domain_mx),
                    line=r.line,
                )
                try:
                    result_data = yield self.domain_patch(domain, **base_new_dict)

                except Exception as err:
                    log_data = dict(
                        domain_name=domain_name,
                        username=self.request_username,
                        action="API",
                        record='账号别名：{}， 错误信息：{}'.format(account_obj.alias_name, str(err)),
                        state="失败"
                    )
                    session.add(DomainOptLog(**log_data))
                    return self.write(dict(code=-1, msg='{}，详情请看日志'.format(action)))
                ###

                ### 记录修改
                if result_data:
                    log_state = "成功"
                    session.query(DomainRecords).filter(DomainRecords.id == int(r.id)).update(
                        {DomainRecords.state: data.get('action')})
                else:
                    log_state = "失败"

                log_data = dict(
                    domain_name=domain_name,
                    username=self.request_username,
                    action=action,
                    record='记录：{}，值：{}，线路：{}，{}'.format(r.domain_rr, r.domain_value, r.line, action),
                    state=log_state
                )
                session.add(DomainOptLog(**log_data))

                if not result_data: return self.write(dict(code=-2, msg='{}，详情请看日志'.format(action)))
        return self.write(dict(code=0, msg='{}完成'.format(action)))

    @run_on_executor(executor='_thread_pool')
    def domain_delete(self, domain, **base_new_dict):
        return domain.del_record(**base_new_dict)

    @gen.coroutine
    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        select_list = data.get('select_list')
        if not select_list: return self.write(dict(code=1, msg='关键参数不能为空'))

        with DBContext('r') as session:
            select_record = session.query(DomainRecords).filter(DomainRecords.id.in_(select_list)).all()
            if select_record and len(select_record) > 0:
                record_obj = select_record[0]
                domain_name = record_obj.domain_name
                account_obj = session.query(DomainCloudConf).filter(
                    DomainCloudConf.alias_name == record_obj.account).first()
                domain_obj = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()
            else:
                return self.write(dict(code=-1, msg='参数有误'))

        if account_obj.cloud_name in ['GoDaddy', 'godaddy']:
            return self.write(dict(code=3, msg='GoDaddy 接口有BUG，暂时不支持删除'))

        domain = domain_factory(account_obj.cloud_name, domain_id=domain_obj.domain_id,
                                access_id=account_obj.access_id,
                                access_key=account_obj.access_key, domain_name=domain_name)

        with DBContext('w', None, True) as session:
            for r in select_record:
                try:
                    del_dict = dict(
                        domain_name=domain_name,
                        record_id=r.record_id,
                        domain_rr=r.domain_rr,
                        domain_type=r.domain_type
                    )
                    result_data = yield self.domain_delete(domain, **del_dict)
                    # result_data = domain.del_record(**del_dict)
                except Exception as err:
                    log_data = dict(
                        domain_name=domain_name,
                        username=self.request_username,
                        action="API",
                        record='账号别名：{}， 错误信息：{}'.format(account_obj.alias_name, str(err)),
                        state="失败"
                    )
                    session.add(DomainOptLog(**log_data))
                    return self.write(dict(code=-1, msg='删除失败，详情请看日志'))

                if result_data:
                    session.query(DomainRecords).filter(DomainRecords.id == int(r.id)).delete(synchronize_session=False)

                log_data = dict(
                    domain_name=domain_name,
                    username=self.request_username,
                    action='删除',
                    record='记录：{}，值：{}，线路：{}'.format(r.domain_rr, r.domain_value, r.line),
                    state='成功'
                )
                session.add(DomainOptLog(**log_data))
                if not result_data: return self.write(dict(code=-2, msg='删除失败，详情请看日志'))

        self.write(dict(code=0, msg='删除成功'))


class DomainOptLogHandler(BaseHandler):
    def get(self, *args, **kwargs):
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=1000, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)

        search_v = self.get_argument('search_value', default=None, strip=True)
        domain_name = self.get_argument('domain_name', default=None, strip=True)

        if not domain_name: return self.write(dict(code=0, msg='关键参数域名不能为空'))

        with DBContext('r') as session:
            if search_v:
                the_count = session.query(DomainOptLog).filter(DomainOptLog.domain_name == domain_name,
                                                               or_(DomainOptLog.username.like(
                                                                   '{}%'.format(search_v)),
                                                                   DomainOptLog.action.like(
                                                                       '{}%'.format(search_v)),
                                                                   DomainOptLog.record.like('{}%'.format(search_v)),
                                                                   DomainOptLog.state.like(
                                                                       '{}%'.format(search_v)),
                                                                   DomainOptLog.state.like('{}%'.format(search_v)),
                                                                   DomainOptLog.update_time.like(
                                                                       '{}%'.format(search_v)),
                                                                   DomainOptLog.id.like(
                                                                       '{}%'.format(search_v)))).count()

                log_info = session.query(DomainOptLog).filter(DomainOptLog.domain_name == domain_name,
                                                              or_(DomainOptLog.username.like(
                                                                  '{}%'.format(search_v)),
                                                                  DomainOptLog.action.like(
                                                                      '{}%'.format(search_v)),
                                                                  DomainOptLog.record.like('{}%'.format(search_v)),
                                                                  DomainOptLog.state.like(
                                                                      '{}%'.format(search_v)),
                                                                  DomainOptLog.state.like('{}%'.format(search_v)),
                                                                  DomainOptLog.update_time.like(
                                                                      '{}%'.format(search_v)),
                                                                  DomainOptLog.id.like(
                                                                      '{}%'.format(search_v)))).order_by(
                    -DomainOptLog.id).offset(limit_start).limit(int(limit))
            else:
                the_count = session.query(DomainOptLog).filter(DomainOptLog.domain_name == domain_name).count()
                log_info = session.query(DomainOptLog).filter(DomainOptLog.domain_name == domain_name).order_by(
                    -DomainOptLog.id).offset(limit_start).limit(int(limit))

        record_log_list = queryset_to_list(log_info)
        self.write(dict(code=0, msg='获取成功', data=record_log_list, count=the_count))


class RecordRemarkHandler(BaseHandler):
    _thread_pool = ThreadPoolExecutor(5)

    @run_on_executor(executor='_thread_pool')
    def record_remark_post(self, domain, **base_new_dict):
        return domain.remark(**base_new_dict)

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        the_id = data.get('id')
        remark = data.get('remark')
        if not the_id or not remark:  self.write(dict(code=0, msg='关键参数域名不能为空'))

        with DBContext('w', None, True) as session:

            record_obj = session.query(DomainRecords).filter(DomainRecords.id == int(the_id)).first()
            account_obj = session.query(DomainCloudConf).filter(
                DomainCloudConf.alias_name == record_obj.account).first()
            session.query(DomainRecords).filter(DomainRecords.id == int(the_id)).update({'remark': remark})
            domain_name = record_obj.domain_name
            ### 开始调用api
            if account_obj.cloud_name in ['阿里云', 'aliyun']:
                domain_obj = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()
                try:
                    domain = domain_factory(account_obj.cloud_name, domain_id=domain_obj.domain_id,
                                            access_id=account_obj.access_id, access_key=account_obj.access_key,
                                            domain_name=domain_name)

                    base_new_dict = dict(domain_name=domain_name, record_id=record_obj.record_id, remark=remark)
                    result_data = yield self.record_remark_post(domain, **base_new_dict)

                except Exception as err:
                    log_data = dict(
                        domain_name=record_obj.domain_name,
                        username=self.request_nickname,
                        action="API",
                        record='账号别名：{}， 错误信息：{}'.format(account_obj.alias_name, str(err)),
                        state="失败"
                    )
                    session.add(DomainOptLog(**log_data))
                    return self.write(dict(code=-1, msg='删除失败，详情请看日志'))
            ### 录入日志
            log_data = dict(
                domain_name=domain_name,
                username=self.request_nickname,
                action='变更备注',
                state="成功",
                record='类型：{}，{}：，记录：{}，线路：{}，备注变更：{} >{}'.format(record_obj.domain_type,
                                                                  record_obj.domain_rr,
                                                                  record_obj.domain_value, record_obj.line,
                                                                  record_obj.remark, remark))
            session.add(DomainOptLog(**log_data))

        self.write(dict(code=0, msg='修改成功'))


class CloudAccountHandler(BaseHandler):
    def get(self, *args, **kwargs):
        with DBContext('r') as session:
            domain_info = session.query(DomainCloudConf).all()

        account_list = []
        for info in domain_info:
            data_dict = model_to_dict(info)
            data_dict['access_key'] = '**********不可查询**********'
            account_list.append(data_dict)

        self.write(dict(code=0, msg='获取成功', data=account_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        alias_name = data.get('alias_name')
        cloud_name = data.get('cloud_name')
        cloud_code = data.get('cloud_code')
        access_id = data.get('access_id')
        access_key = data.get('access_key')
        if not alias_name or not cloud_name or not access_id or not access_key:  return self.write(
            dict(code=-1, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            is_exist = session.query(DomainCloudConf.id).filter(DomainCloudConf.alias_name == alias_name).first()
            if is_exist: return self.write(dict(code=-2, msg='当前账号已经存在，别名不能重复'))

            session.add(DomainCloudConf(alias_name=alias_name, cloud_name=cloud_name, cloud_code=cloud_code,
                                        access_id=access_id, access_key=access_key))

        self.write(dict(code=0, msg='添加成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        the_id = data.get('id')
        cloud_name, cloud_code = data.get('cloud_name'), data.get('cloud_code')
        access_id, access_key = data.get('access_id'), data.get('access_key')
        if not the_id or not cloud_name or not access_id or not access_key:  return self.write(
            dict(code=-1, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            session.query(DomainCloudConf).filter(DomainCloudConf.id == int(the_id)).update(
                {DomainCloudConf.cloud_name: cloud_name,
                 DomainCloudConf.cloud_code: cloud_code,
                 DomainCloudConf.access_id: access_id,
                 DomainCloudConf.access_key: access_key})

        return self.write(dict(code=0, msg='修改完成'))

    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        state, the_id = data.get('state'), data.get('id')

        if not isinstance(state, bool): return self.write(dict(code=-1, msg='数据有误'))
        if not the_id: return self.write(dict(code=-2, msg='关键参数不能为空!'))

        with DBContext('w', None, True) as session:
            session.query(DomainCloudConf).filter(DomainCloudConf.id == int(the_id)).update(
                {DomainCloudConf.state: state})

        if state:  return self.write(dict(code=0, msg='启用成功'))
        return self.write(dict(code=0, msg='禁用成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        del_id = data.get('del_id')
        if not del_id: return self.write(dict(code=1, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            session.query(DomainCloudConf).filter(DomainCloudConf.id == int(del_id)).delete(synchronize_session=False)

        self.write(dict(code=0, msg='删除成功'))


class DomainInfoSync(BaseHandler):
    _thread_pool = ThreadPoolExecutor(5)

    @run_on_executor(executor='_thread_pool')
    def domain_sync(self):
        domain_main('阿里云')
        domain_main('腾讯云')
        domain_main('DNSPod')
        domain_main('GoDaddy')
        return dict(code=0, msg='更新完毕')

    @gen.coroutine
    def get(self, *args, **kwargs):
        res = yield self.domain_sync()
        return self.write(res)


cloud_domain_urls = [
    (r"/v1/dns/cloud/domain/", CloudDomainHandler),
    (r"/v1/dns/cloud/record/", CloudRecordHandler),
    (r"/v1/dns/cloud/logs/", DomainOptLogHandler),
    (r"/v1/dns/cloud/sync/", DomainInfoSync),
    (r"/v1/dns/cloud/remark/", RecordRemarkHandler),
    (r"/v1/dns/cloud/account/", CloudAccountHandler),
]
