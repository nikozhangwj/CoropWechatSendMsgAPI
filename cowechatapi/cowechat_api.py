# !/usr/bin/env python
# encoding: utf-8
# author: niko.zhang
# py_ver: py3

"""
调用企业微信消息接口发送消息
可以指定某个用户、某个部门或者某个标签内的所有人员
初始化对象需要输入企业ID,应用Secret和AgentId
密钥需要现在企业微信后台建立应用后才能获取
该代码需要在python3下的环境执行，不然会报消息类型错误
UPDATE: 20200812
"""

import os
import json
import requests
import logging
import platform
from datetime import datetime


class CoWechatAPI(object):
    LOG_DATE = datetime.now()
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    LOG_FILENAME = 'CWAPI.{}.log'.format(LOG_DATE.strftime("%Y%m%d"))
    DATE_FORMAT = "%m/%d/%Y %H:%M:%S"
    logging.basicConfig(
        filename=LOG_FILENAME,
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT
    )
    try:
        tmp_folder = os.environ['TMP']
    except KeyError:
        if platform.system() == "Linux":
            tmp_folder = os.environ['HOME']
        elif platform.system() == "Windows":
            tmp_folder = os.environ['HOMEPATH']
        else:
            tmp_folder = os.getcwd()

    def __init__(self, coid, secret, agentid):
        # 设置企业微信的coropid和corpsecret, cache用来缓存token
        self.ID = coid
        self.SECRET = secret
        self.agentid = agentid
        self.token = ""
        self.cache = os.path.join(self.tmp_folder, '.token_cache')
        # 重试次数
        self.retry_count = 5
        self.login()

    # 企业微信的coropid和corpsecret写死的话不用执行login
    def login(self):
        if not self.ID and not self.SECRET:
            logging.error('Please input valid ID and SECRET.')
            return False
        self.token = self.get_access_token()

    # 用来保存token到缓存文件
    def save_token(self, token_dict):
        token_dict['date'] = datetime.strftime(datetime.now(), "%Y-%m-%d %H%M%S")
        with open(self.cache, 'wt') as fhandler:
            fhandler.write(json.dumps(token_dict, indent=4))

    # 通过时间判断token是否有效，token有效时间为两个小时
    def token_valid(self):
        if not os.path.exists(self.cache):
            logging.info('token_cache has not found.')
            return False
        with open(self.cache, 'rt') as fhandler:
            data = json.loads(fhandler.read())
            if data['errmsg'] != 'ok':
                logging.error('Cache has no token but error message: ' + data['errmsg'])
                return False
            else:
                logging.info('Cache has no error message.')
            token_date = data['date']
            usetime = (datetime.now() - datetime.strptime(token_date, "%Y-%m-%d %H%M%S")).seconds
            if usetime >= 7200:
                logging.info('Cache token is overtime, get new token from url.')
                return False
            else:
                logging.info('Cache token is valid, get token from cache.')
                return True

    # 通过企业微信API重新获取token
    def get_access_token_url(self):
        token_url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}".format(self.ID,
                                                                                                  self.SECRET)
        try:
            res = requests.get(token_url)
        except BaseException as error:
            print(error)
            return False
        res_dict = res.json()
        logging.info('Get token from token_url.')
        logging.debug(res_dict)
        try:
            res_dict.get('access_token')
        except KeyError as error:
            logging.error(error)
            return False
        self.save_token(res_dict)
        return res_dict['access_token']

    # 通过缓存文件获取token
    def get_access_token_cache(self):
        with open(self.cache, 'rt') as fhandler:
            data = json.loads(fhandler.read())
            logging.info('Get token from cache.')
            logging.debug(data)
            try:
                return data['access_token']
            except KeyError as error:
                logging.error(error)
                return False

    # 获取token功能
    def get_access_token(self):
        if self.token_valid():
            return self.get_access_token_cache()
        else:
            return self.get_access_token_url()

    # 消息前置: 消息分类构造再传入发送方法
    def send(self, msg_type=None, to_user="", to_party="", to_tag="", content=None, media_id=None):

        send_data = {
            "touser": to_user,
            "toparty": to_party,
            "totag": to_tag,
            "msgtype": msg_type,
            "agentid": self.agentid,
            "safe": 0
        }

        if not msg_type:
            logging.error('msg_type can not be None.')
            raise Exception("msg_type can not be None.")

        if msg_type == "text":
            send_data["text"] = {
                "content": content
            }
            logging.info('Start send {} message.'.format(msg_type))
            logging.debug(send_data)
        elif msg_type == "image" and media_id:
            send_data["image"] = {
                "media_id": media_id
            }
            logging.info('Start send {} message.'.format(msg_type))
            logging.debug(send_data)
        elif msg_type == "voice" and media_id:
            send_data["voice"] = {
                "media_id": media_id
            }
            logging.info('Start send {} message.'.format(msg_type))
            logging.debug(send_data)
        elif msg_type == "video" and media_id:
            send_data["video"] = {
                "media_id": media_id,
                "title": "Title",
                "description": "Description"
            }
            logging.info('Start send {} message.'.format(msg_type))
            logging.debug(send_data)
        elif msg_type == "file" and media_id:
            send_data["file"] = {
                "media_id": media_id
            }
            logging.info('Start send {} message.'.format(msg_type))
            logging.debug(send_data)
        else:
            logging.error("data error")
            raise Exception("Message type:{} or arguments invalid, please check yourself.".format(msg_type))

        count = 0
        while count < self.retry_count:
            if self._send_util(send_data=send_data):
                return True
            count += 1
        return False

    # 消息发送方法
    def _send_util(self, send_data):
        send_url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}".format(self.token)
        res = requests.post(send_url, json=send_data)
        res_dict = res.json()
        logging.debug(res_dict)
        if res_dict["errcode"] == 0:
            logging.info('Send message response: ' + res_dict["errmsg"])
            return True
        else:
            logging.error('Send message error response: ' + res_dict["errmsg"])
            raise Exception(res_dict["errmsg"])

    # 上传临时素材
    def upload(self, filetype, fileurl):
        if not filetype or not fileurl:
            logging.error("Missing args error")
        token = self.get_access_token()
        upload_url = "https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={}&type={}".format(token, filetype)
        files = {
            'file': open(fileurl, 'rb')
        }
        response = requests.post(url=upload_url, files=files)
        logging.info(response.status_code)
        logging.info(response.text)
        return response.text