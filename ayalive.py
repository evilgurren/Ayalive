#coding:utf-8
#e.g.: python dyalive.py sourcefile
#域名和非域名-ip-存活(ping\禁ping)-web端口(socket发包探测)-url目录openurl
import os
import re
import sys
# import Queue
import socket
import urllib2
import threading
import threadpool

#设置全局变量扫描完成总数
#抓取ip地址
regex1 = '((25[0-5]|2[0-4]{1}[0-9]{1}|1[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])\.\
		   (25[0-5]|2[0-4]{1}[0-9]{1}|1[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])\.\
		   (25[0-5]|2[0-4]{1}[0-9]{1}|1[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])\.\
		   (25[0-5]|2[0-4]{1}[0-9]{1}|1[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9]))'
#抓取域名
regex2 = '([^w^.^/]+(\.\w+)+)'
#检测常用端口开放情况
List = [21, 23, 80, 135, 137, 445, 1099, 1199, 1433, 3389, 8080]
#最大线程数
Max_threads = 50
#存储主机类的队列
# queue = Queue.Queue()
#互斥锁，保证依次打印数据
mutex = threading.Lock()

urllist = []


#定义主机类，存储url相关信息
class Host(object):
	def __init__(self, url, ip, ping, port, code):
		self.url = url
		self.ip = ip
		self.ping = ping
		self.port = port
		self.code = code
	def getInfo(self):
		if mutex.acquire():
			if self.code != '404':
				s = 'url:' + self.url + '\t' + 'HTTPcode:' + self.code + '\n'
				print s
				urllist.append(self.url) 
			# print 'url:'+self.url+'\t'+'ip:'+self.ip+'\t'+u'ping:'+self.ping+'\t'+'HTTPcode:'+self.code+'\t',
			# print u'port:',
			# for i in self.port:
			# 	print i,
			mutex.release() 

#从url里抓取主机ip地址，如果是域名则查找对应ip
def getIp(url):
	resp = re.search(regex1, url)
	if resp:
		ip = resp.group()
	else:
		# return False
		resp = re.search(regex2, url)
		hostname = resp.group()
		#通过socket找域名对应ip地址
		ip = socket.gethostbyname(hostname)
	return ip

def pinger(host):
	#可根据实际情况调整ping参数，如增加-w参数加快速度，但会降低精准度
	args = 'ping ' + host.ip
	data = os.popen(args)
	for i in data.readlines()[2:6]:
		#通过系统返回值里是否有TTL字段判断是否ping通
		if ('TTL' in i or 'ttl' in i):
			host.ping = 'open'

#检测开放端口、web服务运行情况和能否ping通
def test(host):
	# #从队列里取出主机类
	# host = queue.get()
	if 'http' not in host.url:
		host.url = 'http://' + host.url
	pinger(host)
	#设定超时时间
	timeout = 5
	#伪装成普通浏览器
	headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0'}
	try:
		#urlopen获取HTTP返回码
		rep = urllib2.Request(host.url, None, headers)
		response = urllib2.urlopen(rep, None, timeout)
		host.code = str(response.getcode())
		response.close()
	except urllib2.HTTPError, e:
		host.code = str(e.code)
	except urllib2.URLError, e:
		pass
	except socket.timeout, e:
		pass
	#创建socket实例
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	#设置connect超时时间
	s.settimeout(timeout)
	#检测敏感端口开放情况并记录
	for i in List:
		try:
			s.connect((host.ip, i))
			host.port.append(i)
			s.close()
		except socket.error, e:
			pass
	#输出主机的检查信息
	host.getInfo()
	# queue.task_done()

def main():
	#创建线程，最多50
	# for i in range(Max_threads):
	# 	t = threading.Thread(target=test, args=(queue,))
	# 	t.setDaemon(True)
	# 	t.start()

	# 主机类列表
	list_host = []

	# 创建线程池
	pool = threadpool.ThreadPool(Max_threads)

	#从传参文件里读出url，带http或https协议头
	with open('url.txt', 'r') as file:
		for url in file:
			print url
			ip = getIp(url.strip())
			#初始化类，默认0表示ping不通，开放端口为空，连接为404错误
			if not ip:
				continue
			host = Host(url.strip(), ip, 'close', [], '404')
			list_host.append(host)
		# 	#加入队列
		# 	queue.put(host)
		# #待队列为空再往下运行
		# queue.join()

	requests = threadpool.makeRequests(test, list_host)
	[pool.putRequest(req) for req in requests] 
	pool.wait()

	with open('aliveurl.txt', 'w') as file:
		for url in urllist:
			file.write(url + '\n')

if __name__ == '__main__':
	main()