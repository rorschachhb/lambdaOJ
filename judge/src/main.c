#include "judge.h"
#include "csapp.h"
#include "cJSON.h"

#define PORT 8787
#define MAX_JSON_REQ_SIZE 4096

void reap() 
{
    while (waitpid(-1,0,WNOHANG) > 0) ;
    return ;
}

int main() {
    init_lang_config() ;
    init_banned_syscall();
    int listenfd, connfd, port, clientlen ;
    struct sockaddr_in clientaddr;
    listenfd = Open_listenfd(PORT) ;
    
    redisContext *c = redisConnect("127.0.0.1",6379) ;
    
    while (1) {
	clientlen = sizeof(clientaddr) ;
	connfd = Accept(listenfd,(SA*)&clientaddr,&clientlen) ;
	reap() ;
	if (Fork() == 0) {
	    Close(listenfd) ;
	    char json_req[MAX_JSON_REQ_SIZE]={0} ;
	    int nbytes ;
	    nbytes = recv(connfd,json_req,MAX_JSON_REQ_SIZE,0) ;
	    if (nbytes < 0) {
		unix_error("recv json error!");
		exit(127) ;
	    }
	    cJSON *request ;
	    request = cJSON_Parse(json_req) ;
	    if(!request) {
		unix_error("Json parse error!") ;
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
	    int i ; int ac_num = 0 ;
	    for(i=0;i<test_num;i++) {
		struct judge_result* jr ;
		jr = (struct judge_result*)calloc(1,sizeof(struct judge_result)) ;
		char test_in[128] = {0} ; 
		sprintf(test_in,"%s/%d.in",test_dir,i) ;
		char test_ans[128] = {0} ;
		sprintf(test_ans,"%s/%d.ans",test_dir,i) ;
		judge_exe(test_in,test_ans,output,
			  cJSON_GetArrayItem(time_limit_arr,i)->valueint,
			  cJSON_GetArrayItem(mem_limit_arr,i)->valueint,jr,
			  lc->exe_cmd,lc->exe_args) ;
		if(jr->state==AC) ac_num++;
		redisCommand(c,"HMSET lambda:%d:result:%d state %s time %ld memory %ld bad_syscall %d",
			     submit_id,i, state_string[jr->state],jr->time_ms,jr->mem_kb, jr->bad_syscall_number);
	    }
	    float rate = (ac_num+0.0)/(test_num+0.0) ;
	    redisCommand(c,"HMSET lambda:%d:head state %.2f",submit_id,rate);
	    execlp("/usr/bin/rm","rm","-rf",work_dir,NULL);
	    exit(0);
	}
	Close(connfd) ;
    }
    return 0 ;
}
