#!/usr/bin/env python
import os
import json
import socket
import redis
import time

base_dir = os.path.abspath(os.path.dirname(__file__))

test_type = os.listdir('./test_filed')
sid = 0

r = redis.Redis('127.0.0.1',6379)

for each_type in test_type :
	print 40*'-'
	print "test for %s" % each_type
	json_req = {"submit_id" : sid, \
                    "code_path" : os.path.join(base_dir, "test_filed",\
                                  each_type,each_type+'.c'),\
                    "test_sample_num" : 2,\
                    "lang_flag" : 0,\
                    "work_dir" : os.path.join(base_dir,"test_filed",\
                                 each_type,"work"),\
                    "test_dir" : os.path.join(base_dir,"test_filed",\
                                 each_type,"sample"),\
		    "time_limit" : [2,2],
                    "mem_limit" : [10000,10000]}
	os.system("mkdir %s" % json_req["work_dir"])
	text = json.dumps(json_req)
	s = socket.socket()
	s.connect(('127.0.0.1',8787))
	n = s.send(text)
	print "send %d bytes json text" % n
	s.close()
	time.sleep(7)
	print "get head..."
	print r.hgetall("lambda:%d:head" % sid)
	print "print result..."
	for i in range(2) : print r.hgetall("lambda:%d:result:%d" % (sid,i))
	
	aa = raw_input('press any key to continue')
	sid = sid + 1
