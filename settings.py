#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019年5月6日
Desc    : 配置文件
"""

import os
from websdk.consts import const

ROOT_DIR = os.path.dirname(__file__)
debug = True
xsrf_cookies = False
expire_seconds = 365 * 24 * 60 * 60
cookie_secret = '61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2X6TP1o/Vo='

DEFAULT_DB_DBHOST = os.getenv('DEFAULT_DB_DBHOST', '172.16.0.223')
DEFAULT_DB_DBPORT = os.getenv('DEFAULT_DB_DBPORT', '3306')
DEFAULT_DB_DBUSER = os.getenv('DEFAULT_DB_DBUSER', 'root')
DEFAULT_DB_DBPWD = os.getenv('DEFAULT_DB_DBPWD', 'ljXrcyn7chaBU4F')
DEFAULT_DB_DBNAME = os.getenv('DEFAULT_DB_DBNAME', 'codo_dns')

READONLY_DB_DBHOST = os.getenv('READONLY_DB_DBHOST', '172.16.0.223')
READONLY_DB_DBPORT = os.getenv('READONLY_DB_DBPORT', '3306')
READONLY_DB_DBUSER = os.getenv('READONLY_DB_DBUSER', 'root')
READONLY_DB_DBPWD = os.getenv('READONLY_DB_DBPWD', 'ljXrcyn7chaBU4F')
READONLY_DB_DBNAME = os.getenv('READONLY_DB_DBNAME', 'codo_dns')

named_init_conf = """
options {
    //listen-on port 53 { 127.0.0.1; };
    //listen-on-v6 port 53 { ::1; };
    directory     "/var/named";
    dump-file     "/var/named/data/cache_dump.db";
        statistics-file "/var/named/data/named_stats.txt";
        memstatistics-file "/var/named/data/named_mem_stats.txt";
    //allow-query     { localhost; };
    recursion yes;

    dnssec-enable no;
    dnssec-validation no;
    dnssec-lookaside auto;

    allow-query-cache { any; };
    allow-query { any; };

    /* Path to ISC DLV key */
    //bindkeys-file "/etc/named.iscdlv.key";

    //managed-keys-directory "/var/named/dynamic";
};
//----------------------------------------
//-------------- smart DNS ---------------
//----------------------------------------
//------------------ NW -------------------
include "/etc/named.neiwang.conf";
view "View_NW" {
    match-clients { NW; };

    //example_neiwang
    /* zone "example.com" IN {
        type master;
        file "example.com-neiwang.zone";
        allow-update { none; };
    }; */
};
//----------------- CU -------------------
include "/etc/named.liantong.conf";
view "View_CU" {
    match-clients { CU; };
    //example_liantong
    /* zone "example.com" IN {
        type master;
        file "example.com-liantong.zone";
        allow-update { none; };
    }; */
};
//----------------- CT -------------------
include "/etc/named.dianxin.conf";
view "View_CT" {
    match-clients { CT; };

    //example_dianxin
    /* zone "example.com" IN {
        type master;
        file "example.com-dianxin.zone";
        allow-update { none; };
    }; */
};
//---------------- CERNET ----------------
include "/etc/named.jiaoyu.conf";
view "View_CERNET" {
    match-clients { CERNET; };

    //example_jiaoyu
    /* zone "example.com" IN {
        type master;
        file "example.com-jiaoyu.zone";
        allow-update { none; };
    }; */
};
//---------------- ANY ----------------
view "View_ANY" {
    match-clients { any; };

    //example_any
    /* zone "example.com" IN {
        type master;
        file "example.com.zone";
        allow-update { none; };
    }; */
};
"""

# region_init_conf = dict(any='默认', neiwang='内网', dianxin='电信', liantong='联通', jiaoyu='教育', guonei='国内',
#                         huadong='华东', huazhong='华中', huanan='华南', huabei='华北', dongbei='东北', xibei='西北',
#                         xinan='西南')
region_init_conf = dict(默认='any', 内网='neiwang', 电信='dianxin', 联通='liantong', 教育='jiaoyu')

try:
    from local_settings import *
except:
    pass

settings = dict(
    debug=debug,
    xsrf_cookies=xsrf_cookies,
    cookie_secret=cookie_secret,
    expire_seconds=expire_seconds,
    app_name='codo-dns',
    named_init_conf=named_init_conf,
    region_init_conf=region_init_conf,
    databases={
        const.DEFAULT_DB_KEY: {
            const.DBHOST_KEY: DEFAULT_DB_DBHOST,
            const.DBPORT_KEY: DEFAULT_DB_DBPORT,
            const.DBUSER_KEY: DEFAULT_DB_DBUSER,
            const.DBPWD_KEY: DEFAULT_DB_DBPWD,
            const.DBNAME_KEY: DEFAULT_DB_DBNAME,
        },
        const.READONLY_DB_KEY: {
            const.DBHOST_KEY: READONLY_DB_DBHOST,
            const.DBPORT_KEY: READONLY_DB_DBPORT,
            const.DBUSER_KEY: READONLY_DB_DBUSER,
            const.DBPWD_KEY: READONLY_DB_DBPWD,
            const.DBNAME_KEY: READONLY_DB_DBNAME,
        }
    }
)
