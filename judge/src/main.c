#include "judge.h"
#include "csapp.h"
#include "cJSON.h"

#define PORT 8787
#define MAX_JSON_REQ_SIZE 4096

static char curr_time[32] ;
struct tm *ct;

void reap() 
{
    while (waitpid(-1,0,WNOHANG) > 0) ;
    return ;
}

int main() 
{
    openlog("lambdaoj",LOG_PID,LOG_USER);
    init_lang_config() ;
    syslog(LOG_INFO,"%s","language config loaded successfully from redis") ;
    init_banned_syscall();
    syslog(LOG_INFO,"%s","system call black list loaded successfully from redis") ;
    int listenfd, connfd, port, clientlen ;
    struct sockaddr_in clientaddr;
    listenfd = Open_listenfd(PORT) ;
    redisContext *c = redisConnect("127.0.0.1",6379) ;
    
    while (1) {
	clientlen = sizeof(clientaddr) ;
	connfd = Accept(listenfd,(SA*)&clientaddr,&clientlen) ;
	reap() ;
	if (Fork() == 0) {
	    syslog(LOG_INFO,"%s","new process for juding user code");
	    Close(listenfd) ;
	    char json_req[MAX_JSON_REQ_SIZE]={0} ;
	    int nbytes ;
	    nbytes = recv(connfd,json_req,MAX_JSON_REQ_SIZE,0) ;
	    if (nbytes < 0) {
		syslog(LOG_ERR,"%s","recv json error!") ;
		exit(127) ;
	    }
	    syslog(LOG_INFO,"recv %d bytes json data",nbytes) ;
	    cJSON *request ;
	    request = cJSON_Parse(json_req) ;
	    if(!request) {
		syslog(LOG_ERR,"parse json error!");
		exit(127) ;
	    }
	    close(connfd) ;

	    int test_num, lang_flag ;
	    int submit_id ;
	    submit_id = cJSON_GetObjectItem(request,"submit_id")->valueint;
	    test_num = cJSON_GetObjectItem(request,"test_sample_num")->valueint;
	    lang_flag = cJSON_GetObjectItem(request,"lang_flag")->valueint;
	    char *code_path = cJSON_GetObjectItem(request,"code_path")->valuestring ;
	    char *work_dir = cJSON_GetObjectItem(request,"work_dir")->valuestring ;
	    char *test_dir = cJSON_GetObjectItem(request,"test_dir")->valuestring ;
	    cJSON* time_limit_arr = cJSON_GetObjectItem(request,"time_limit") ;
	    cJSON* mem_limit_arr = cJSON_GetObjectItem(request,"mem_limit") ;
            cJSON* weights = cJSON_GetObjectItem(request,"weights") ;
	    
	    syslog(LOG_INFO,"submit_id : %d", submit_id) ;
	    syslog(LOG_INFO,"test_sample_num : %d",test_num) ;
	    syslog(LOG_INFO,"lang_flag : %d", lang_flag); 
	    syslog(LOG_INFO,"code_path : %s", code_path) ;
	    syslog(LOG_INFO,"work_dir : %s", work_dir) ;
	    syslog(LOG_INFO,"test_dir : %s", test_dir) ;

	    chdir(work_dir) ;//change current working directory
	    
	    struct lang_config *lc ;
	    lc = (struct lang_config*)calloc(1,sizeof(struct lang_config));
	    set_lang_option(lc,lang_flag,code_path) ;
	    char err_file[128] = {0} ;
	    sprintf(err_file,"%s/err",work_dir) ;
	    compile_code(lc->compile_cmd,
			 lc->compile_args,
			 err_file) ;
	    //test err_file size
	    int err_fd ;
	    struct stat buf ;
	    err_fd = open(err_file,O_RDONLY) ;
	    fstat(err_fd,&buf) ;
	    if (buf.st_size>0) {
		char *err_message ;
		err_message = (char*)calloc(1,buf.st_size+1) ;
		read(err_fd,err_message,buf.st_size) ;
		redisCommand(c,"HMSET lambda:%d:head state %s err_message %s", 
			     submit_id,state_string[CE],err_message) ;
	        execlp("/usr/bin/rm","rm","-rf",work_dir,NULL);
		exit(0) ;
	    }

	    char output[128] = {0} ;
	    sprintf(output,"%s/output",work_dir) ;
	    int i ; int rate = 0 ;
            
	    for(i=0;i<test_num;i++) {
		struct judge_result* jr ;
		jr = (struct judge_result*)calloc(1,sizeof(struct judge_result)) ;
		char test_in[128] = {0} ; 
		sprintf(test_in,"%s/%d.in",test_dir,i) ;
		char test_ans[128] = {0} ;
		sprintf(test_ans,"%s/%d.ans",test_dir,i) ;
                pid_t test_pid ;
                test_pid = fork() ;
                if (test_pid == 0) {
                  judge_exe(test_in,test_ans,output,
                            cJSON_GetArrayItem(time_limit_arr,i)->valueint,
                            cJSON_GetArrayItem(mem_limit_arr,i)->valueint,jr,
                            lc->exe_cmd,lc->exe_args) ;
                  int ac_or_not = jr->state==AC ;
                  redisCommand(c,"HMSET lambda:%d:result:%d state %s time %ld memory %ld bad_syscall %d",
                               submit_id,i, state_string[jr->state],jr->time_ms,jr->mem_kb, jr->bad_syscall_number);
                  exit(ac_or_not) ;
                }
                int ac_status ;
                wait(&ac_status) ;
                int ac_flag =  (WEXITSTATUS(ac_status)) ;
                if (ac_flag) {
                  rate = rate + cJSON_GetArrayItem(weights,i)->valueint;
                }
	    }
            
	    redisCommand(c,"HMSET lambda:%d:head state %d",submit_id,rate);
	    execlp("/usr/bin/rm","rm","-rf",work_dir,NULL);
	    exit(0);
	}
	Close(connfd) ;
    }
    closelog();
    return 0 ;
}
