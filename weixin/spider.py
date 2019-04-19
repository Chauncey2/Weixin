from requests import Session
from weixin.config import *
from weixin.db import RedisQueue
from weixin.mysql import MySQL
from weixin.request import WeixinRequest
from urllib.parse import urlencode
import requests
from pyquery import PyQuery as pq
from requests import ReadTimeout,ConnectionError

class Spider():
    base_url='http://weixin.sogou.com/weixin'
    keyword='Python'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,ja;q=0.4,zh-TW;q=0.2,mt;q=0.2',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Cookie': 'sw_uuid=3609245170; ssuid=6984416384; IPLOC=CN3205; SUID=42E4F03A2208990A000000005CAACCB1; '
                  'SUV=0077C7C03AF0E4425CAACCBA3EAA1002; sg_uuid=4552023396; pgv_pvi=2560417792; '
                  'ld=5kllllllll2t$7hflllllVhmZ1GlllllnsR6yklllx6llllljZlll5@@@@@@@@@@; LSTMV=1233%2C730; LCLKINT=3357;'
                  ' ABTEST=7|1555656250|v1; SNUID=07A2B57C4540C099347CF15446DF5250; weixinIndexVisited=1; sct=28; '
                  'JSESSIONID=aaaEN5dN5s469asWKmQOw; '
                  'ppinf=5|1555657086|1556866686|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZTo3MjolRTQlQjglODAlRTQlQj'
                  'glQUElRTQlQjglOEQlRTQlQkYlOTclRTYlQjAlOTQlRTclOUElODQlRTYlOTglQjUlRTclQTclQjB8Y3J0OjEwOjE1NTU2NTcwODZ'
                  '8cmVmbmljazo3MjolRTQlQjglODAlRTQlQjglQUElRTQlQjglOEQlRTQlQkYlOTclRTYlQjAlOTQlRTclOUElODQlRTYlOTglQjUlR'
                  'TclQTclQjB8dXNlcmlkOjQ0Om85dDJsdU1uRGNFMkVZQ2FMdElITGU2MlZiOXdAd2VpeGluLnNvaHUuY29tfA; '
                  'pprdig=C9hb1VEIXL_gj8VuGmwYAWeDaqQwG5sz6aifKnY1z61mCwAiAliOr_i0ttUjeP0YQy4u24ea3W4YlciR_pOkna68yh'
                  'R-uVUZqG41lBUan5t34Qtq8InIhLWmrnR_HOhTNbvKWFtpS86DEg2E6CZO2zrf-6Sivzeu3l9ZDsRMV7M; '
                  'sgid=00-45162031-AVy5cX5f8XYsibaupx6TZIiak; ppmdig=1555663237000000b769348c00cc240f380a45206d091d03',
        'Host': 'weixin.sogou.com',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36'
    }
    session=Session()
    queue=RedisQueue()
    mysql=MySQL()

    def get_proxy(self):
        """
        从代理池获取代理
        :return:
        """
        try:
            response=requests.get(PROXY_POOL_URL)
            if response.status_code==200:
                print('Get Proxy',response.text)
                return response.text
        except requests.ConnectionError:
            return None

    def start(self):
        """
        初始化工作
        :return:
        """
        # 全局更新Headers
        self.session.headers.update(self.headers)
        start_url=self.base_url+'?'+urlencode({'query':self.keyword,'type':2})
        weixin_request=WeixinRequest(url=start_url,callback=self.parse_index,need_proxy=True)

        # 调度第一个请求
        self.queue.add(weixin_request)

    def parse_index(self,response):
        """
        解析索引页
        :param response: 响应
        :return: 新的响应
        """
        doc=pq(response.text)
        items=doc('.news-box .news-list li .txt-box h3 a').items()
        for item in items:
            url=item.attr('href')
            weixin_request=WeixinRequest(url=url,callback=self.parse_detail)
            yield weixin_request
        next=doc('#sogou_next').attr('href')
        if next:
            url=self.base_url+str(next)
            weixin_request=WeixinRequest(url=url,callback=self.parse_index,need_proxy=True)
            yield weixin_request

    def parse_detail(self,response):
        """
        解析详情页
        :param response:
        :return:
        """
        doc=pq(response.text)
        data = {
            'title': doc('.rich_media_title').text(),
            'content': doc('.rich_media_content').text(),
            'date': doc('#post-date').text(),
            'nickname': doc('#js_profile_qrcode > div > strong').text(),
            'wechat': doc('#js_profile_qrcode > div > p:nth-child(3) > span').text()
        }
        yield data

    def request(self,weixin_request):
        """
        执行请求
        :param weixin_request: 请求
        :return: 响应
        """
        try:
            if weixin_request.need_proxy:
                proxy=self.get_proxy()
                if proxy:
                    proxies={
                        'http':'http://'+proxy,
                        'https':'https://'+proxy
                    }
                    return  self.session.send(weixin_request.prepare())
        except:
            pass










