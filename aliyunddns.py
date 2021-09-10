import json
import requests
import random
import re
import chardet
import os
import time

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest
from aliyunsdkecs.request.v20140526 import StopInstanceRequest

# 此类的作用是获取本地外网ip
class IP(object):
    def __init__(self):
        from tool import user_agent_list
        self.user_agent_list = user_agent_list
        # 网上找了几个获取ip的接口，为了防止过多的访问接口被封，每次调用随机选择
        self.api_list = [
            'http://ip.chinaz.com/getip.aspx',
            'http://www.net.cn/static/customercare/yourip.asp',
            'https://ip.cn/',
            'http://www.ip168.com/json.do?view=myipaddress',
            'http://pv.sohu.com/cityjson',
            'http://pv.sohu.com/cityjson',
            'http://ip.taobao.com/service/getIpInfo.php?ip=myip',
            'http://2018.ip138.com/ic.asp',
        ]

    def ip_query(self):
        # 一直循环，直到成功获取到本地外网ip
        while True:
            url = random.sample(self.api_list, 1)[0]
            headers = random.sample(self.user_agent_list, 1)[0]
            try:
                res = requests.get(url, headers={'User-Agent':headers}, timeout=5)
                encoding = chardet.detect(res.content)['encoding']
                html = res.content.decode(encoding)
                out = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',html)
                if out != []: return out[0]
            except Exception as e:
                continue

#此类是修改阿里云的解析ip
class Aliyunddns(object):
    def __init__(self):
        self.local_ip = IP()
        # 修改以下内容为你自己的，！！！！！！！！！！！！！！
        self.client = AcsClient("修改为你的AccessKey ID","修改为你的Access Key Secret");
        self.domain = '修改为你的顶级域名，注意是顶级域名'

    #检测本地网络环境，是否是联网状态
    def IsConnectNet(self):
        try:
            requests.get('http://www.baidu.com',timeout=5)
            return True
        except requests.exceptions.ConnectionError as e:
            return False

    # 检测本地外网ip是否和解析的ip一致
    def CheckLocalip(self):
        if not self.IsConnectNet():
            print('网络不通...')
            return

        #这里为了防止频繁的访问阿里云api，会把ip存入本地的ip.txt文件中
        #每次都和本地文件中的ip地址进行对比，不一致再去访问阿里云api进行修改
        netip = self.local_ip.ip_query()
        if os.path.exists('ip.txt'):
            with open('ip.txt','r') as fp:
                file_ip = fp.read()

            if file_ip == netip:
                print('IP相同, 不需要重新解析。')
                return
            else:
                print('IP不相同, 开始重新解析...')
                with open('ip.txt','w') as fp:
                    fp.write(netip)
                    fp.close()
                self.GetDomainRecords()
        else:
            print('文件不存在，直接写入外网IP')
            with open('ip.txt','w') as fp: fp.write(netip)

    #开始更新
    def Update(self,ip,record):
        udr = DescribeInstancesRequest.DescribeInstancesRequest()
        udr.set_accept_format('json')
        udr.set_RecordId(record['RecordId'])
        udr.set_RR(record['RR'])
        udr.set_Type(record['Type'])
        udr.set_Value(ip)
        response = self.client.do_action_with_exception(udr)
        UpdateDomainRecordJson = json.loads(response.decode('utf-8'))
        print(UpdateDomainRecordJson)

    #获取阿里云域名解析信息
    def GetDomainRecords(self):
        DomainRecords = DescribeDomainRecordsRequest.DescribeDomainRecordsRequest()
        DomainRecords.set_DomainName(self.domain)
        DomainRecords.set_accept_format('json')
        response = self.client.do_action_with_exception(DomainRecords)
        record_dict = json.loads(response.decode('utf-8'))
        for record in record_dict['DomainRecords']['Record']:
            if not record['RR'] in ['@','www']:
                continue
            netip = self.local_ip.ip_query()

            if record['Value'] != netip:
                print('netip:',netip)
                print('aliip:',record['Value'])
                self.Update(netip, record)

if __name__ == '__main__':
    ali = Aliyunddns()
    while True:
        ali.CheckLocalip()
        # 这里设置检测的时间间隔，单位秒
        time.sleep(60)