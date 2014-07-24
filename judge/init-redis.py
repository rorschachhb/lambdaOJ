#!venv/bin/python

import redis
r = redis.Redis('localhost',6379,db=0)
#set C
r.set('lambda:C:compiler',"/usr/bin/gcc")
r.rpush('lambda:C:compile_args',"gcc","-w","-lm","-o","a.out")
r.set('lambda:C:execute',"./a.out")
r.rpush('lambda:C:execute_args',"a.out")
#set C++
r.set('lambda:C++:compiler',"/usr/bin/g++")
r.rpush('lambda:C++:compile_args',"g++","-w","-lm","-o","a.out")
r.set('lambda:C++:execute',"./a.out")
r.rpush('lambda:C++:execute_args',"a.out")
#set Python2.7
r.set('lambda:Python2.7:compiler',"/usr/bin/py_compiler")
r.rpush('lambda:Python2.7:compile_args',"py_compiler")
r.set('lambda:Python2.7:execute',"/usr/bin/python")
r.rpush('lambda:Python2.7:execute_args',"pyton","./a.out")
