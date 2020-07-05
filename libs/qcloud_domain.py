#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import time
import requests
import json
import hmac
import hashlib
import base64
from urllib import parse


class QCloudApiOpt:

    @staticmethod
    def sort_dic(keydict):
        return sorted(zip(keydict.keys(), keydict.values()))

    @staticmethod
    def get_str_sign(sortlist, api_url):
        sign_str_init = ''
        for value in sortlist:
            sign_str_init += value[0] + '=' + value[1] + '&'
        sign_str = 'GET' + api_url + sign_str_init[:-1]
        return sign_str, sign_str_init

    @staticmethod
    def get_signature(sign_str, secret_key):
        secretkey = secret_key
        signature = bytes(sign_str, encoding='utf-8')
        secretkey = bytes(secretkey, encoding='utf-8')
        my_sign = hmac.new(secretkey, signature, hashlib.sha1).digest()
        return base64.b64encode(my_sign)

    @staticmethod
    def encode_signature(my_sign):
        return parse.quote(my_sign)

    @staticmethod
    def get_result_url(sign_str, result_sign, api_url):
        return 'https://' + api_url + sign_str + 'Signature=' + result_sign

    @staticmethod
    def run(keydict, api_url, secret_key):
        sortlist = QCloudApiOpt.sort_dic(keydict)
        # 获取拼接后的sign字符串
        sign_str, sign_str_int = QCloudApiOpt.get_str_sign(sortlist, api_url)
        # 获取签名
        my_sign = QCloudApiOpt.get_signature(sign_str, secret_key)
        # 对签名串进行编码
        result_sign = QCloudApiOpt.encode_signature(my_sign)
        # 获取最终请求url
        result_url = QCloudApiOpt.get_result_url(sign_str_int, result_sign, api_url)
        return result_url


####
class QCloud:
    def __init__(self, **config):
        self.domain_name = config.get('domain_name')
        self.__access_id = config.get('access_id')
        self.__access_key = config.get('access_key')
        self.length = '100'
        self.alias_name = config.get('alias_name')
        self.api_url = 'cns.api.qcloud.com/v2/index.php?'
        ##

    def create_result_url(self, *args, **kwargs):
        params = {**{'Timestamp': str(int(time.time())),
                     'Nonce': str(int(random.random() * 1000)),
                     'SecretId': self.__access_id},
                  **kwargs.get('data_dict')}
        return QCloudApiOpt.run(params, self.api_url, self.__access_key)

    def describe_record(self, *args, **kwargs):
        params = {'Action': 'RecordList', 'domain': kwargs.get('domain_name'), 'subDomain': kwargs.get('domain_rr')}

        response = requests.get(self.create_result_url(data_dict=params))
        result_data = json.loads(response.text)

        return result_data.get('data').get('records')

    def add_record(self, *args, **kwargs):
        ### 文档中 TTL MX要传入int  其实只能传入str
        if kwargs.get('line') in ['default', 'Default', '默认']:
            line = '默认'
        else:
            line = kwargs.get('line')

        params = {'Action': 'RecordCreate', 'domain': kwargs.get('domain_name'),
                  'subDomain': kwargs.get('domain_rr'), 'recordType': kwargs.get('domain_type'),
                  'recordLine': line, 'value': kwargs.get('domain_value'),
                  'ttl': str(kwargs.get('domain_ttl', 600)), 'mx': str(kwargs.get('domain_mx', 0))}

        response = requests.get(self.create_result_url(data_dict=params))
        result_data = json.loads(response.text)
        if result_data.get('code') == 0:
            return result_data.get('data').get('record').get('id')
        else:
            return False

    def update_record(self, *args, **kwargs):
        if kwargs.get('line') in ['default', 'Default', '默认']:
            line = '默认'
        else:
            line = kwargs.get('line')

        params = {'Action': 'RecordModify', 'domain': kwargs.get('domain_name'),
                  'recordId': kwargs.get('record_id'),
                  'subDomain': kwargs.get('domain_rr'), 'recordType': kwargs.get('domain_type'),
                  'recordLine': line, 'value': kwargs.get('domain_value'),
                  'ttl': str(kwargs.get('domain_ttl', 600)), 'mx': str(kwargs.get('domain_mx', 0))}

        response = requests.get(self.create_result_url(data_dict=params))
        result_data = json.loads(response.text)
        if result_data.get('code') == 0:
            return result_data.get('data').get('record').get('id')
        else:
            return False

    def remark(self, *args, **kwargs):

        return dict(code=0, msg='腾讯云不支持修改')

    def set_record_status(self, *args, **kwargs):
        if kwargs.get('status') in ['开启', '启用', 'Enable', 'enable', 'ENABLE']:
            status = 'enable'
        else:
            status = 'disable'

        params = {'Action': 'RecordStatus', 'domain': kwargs.get('domain_name'),
                  'recordId': kwargs.get('record_id'), 'status': status}

        response = requests.get(self.create_result_url(data_dict=params))

        return json.loads(response.text)

    def del_record(self, *args, **kwargs):
        params = {'Action': 'RecordDelete', 'domain': kwargs.get('domain_name'),
                  'recordId': kwargs.get('record_id')}

        response = requests.get(self.create_result_url(data_dict=params))

        return json.loads(response.text)

    ###############
    def get_domain_url(self, offset='0'):
        api_url = 'cns.api.qcloud.com/v2/index.php?'
        key_dict = {
            # 公共参数部分
            'Timestamp': str(int(time.time())),
            'Nonce': str(int(random.random() * 1000)),
            'SecretId': self.__access_id,
            'offset': str(offset),
            'length': str(self.length),
            # 接口参数部分
            'Action': 'DomainList'
        }
        result_url = QCloudApiOpt.run(key_dict, api_url, self.__access_key)
        return result_url

    def get_record_url(self, domain_name, offset='0'):
        api_url = 'cns.api.qcloud.com/v2/index.php?'
        key_dict = {
            # 公共参数部分
            'Timestamp': str(int(time.time())),
            'Nonce': str(int(random.random() * 1000)),
            'SecretId': self.__access_id,
            'offset': str(offset),
            'length': str(self.length),
            'domain': domain_name,
            'Action': 'RecordList'
        }
        result_url = QCloudApiOpt.run(key_dict, api_url, self.__access_key)
        return result_url

    ### 最大支持到100个域名，就不分页取了。
    def describe_domains(self):
        result_url = self.get_domain_url()
        response = requests.get(result_url)
        result_data = json.loads(response.text)
        return result_data.get('data').get('domains')

    def get_records_page(self, domain_name, offset):
        result_url = self.get_record_url(domain_name, offset)
        response = requests.get(result_url)
        return json.loads(response.text).get('data')

    def describe_records(self, domain_name):
        offset = 0
        while True:
            result_data = self.get_records_page(domain_name, offset)

            if not result_data or 'records' not in result_data: break
            data = result_data.get('records')

            if not data: break
            offset += int(self.length)
            row = data
            if not row: break
            yield row

    def record_generator(self, **domain):
        record_info_list = self.describe_records(domain.get('name'))
        if not record_info_list: return False
        for record_list in record_info_list:
            for record in record_list:
                yield dict(domain_name=domain.get('name'), data_dict=record)
