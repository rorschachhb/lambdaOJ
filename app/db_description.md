#数据库字段说明

##User
nickname：用户昵称  
sid：学号  
email：邮箱，用于登陆  
password：密码  
role：身份，普通用户或管理员，用整形表示  
status：状态，正常或者被封，用整形表示  
last_seen：上次登陆时间  
last_submition：上次提交时间  

##Problem
problem_id：问题编号  
title：标题，有长度限制（100，随手写的）  
time_limit：时间限制，以秒为单位  
memory_limit：内存限制，以kb为单位  
description：问题描述，纯文本  
input_description：输入格式描述，纯文本  
output_description：输出格式描述，纯文本  
input_sample：输入样例，纯文本  
output_sample：输出样例，纯文本  
hint：提示，纯文本  

##Submit
id：主键  
problem：外键，指向Problem表  
user：外键，指向User表  
status：提交结果，照搬poj上的8种结果，用整形表示  
time：消耗时间，以秒为单位  
memory：消耗内存，以kb为单位  
language：语言，暂定C/C++/PYTHON，用整形表示  
submit_time：提交时间  
code_file：字符串，文件在服务器上的存储路径  
error_message：错误信息，纯文本  