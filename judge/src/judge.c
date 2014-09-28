#include "judge.h"
#include "dlfcn.h"

#define LD_PATH "/home/oj/lambdaoj/app/problems/"

#define REDIS_IP "127.0.0.1"
#define REDIS_PORT 6379
#define BUF_SIZE 128

typedef int (*check_function) (char*,char*);

static int syscall_white_list[512] ; 
static sigjmp_buf buf ;
static int max_compile_time = 5;
static int max_output_size = 1024;
static int max_as = 1024*1024*60 ;

static char* support_language[]={"C","C++"};//match enum order
char* state_string[]={"Accepted","Wrong Answer","Time Limit Exceeded","Memory Limit Exceeded","Runtime Error","Compilation Error","Banned Syscall","Output Limit Exceeded"}; //match enum

static redisReply* compiler[CPP+1] ; //
static redisReply* execute[CPP+1] ;
static redisReply* compile_args[CPP+1] ;
static redisReply* execute_args[CPP+1] ;

void init_banned_syscall(){
    redisContext* r= redisConnect(REDIS_IP,REDIS_PORT) ;
    redisReply *re = redisCommand(r,"lrange lambda:banned_syscall 0 -1") ;
    int i ;
    for(i=0;i<re->elements;i++){
	int curr_sysnum = atoi(re->element[i]->str) ;
	syscall_white_list[curr_sysnum] = 1 ;
    }
    freeReplyObject(re);
    redisFree(r) ;
}

void init_lang_config()
{
    redisContext *r = redisConnect(REDIS_IP,REDIS_PORT) ;
    int i ;
    for(i=0;i<=CPP;i++){
	compiler[i] = redisCommand(r,"get lambda:%s:compiler",support_language[i]);
	execute[i] = redisCommand(r,"get lambda:%s:execute",support_language[i]);
	compile_args[i] = redisCommand(r,"lrange lambda:%s:compile_args 0 -1",support_language[i]) ;
	execute_args[i] = redisCommand(r,"lrange lambda:%s:execute_args 0 -1",support_language[i]) ;
    }
    redisFree(r) ;
}

int copy_string_array(redisReply* re, char *args[]) {
    int i ;
    for(i=0;i<re->elements;i++){
	args[i] = re->element[i]->str ;
    }
    return re->elements ;
}

void set_lang_option(struct lang_config* lc, enum lang lang_flag,char *path)
{
    lc->compile_cmd = compiler[lang_flag]->str ;
    lc->exe_cmd = execute[lang_flag]->str;
    int len ;
    len = copy_string_array(compile_args[lang_flag],lc->compile_args) ;
    lc->compile_args[len] = path ; 
    lc->compile_args[len+1] = NULL ;
    len =copy_string_array(execute_args[lang_flag],lc->exe_args) ;
    lc->exe_args[len] = NULL ;
}


void compile_term(int sig)
{
    signal(SIGCHLD,SIG_DFL);
    while (waitpid(-1,0,WNOHANG) > 0) ;
    siglongjmp(buf,1) ;
}

void compile_code(char *compile_cmd,char *argv[],char *err_file)
{
    signal(SIGCHLD,compile_term) ;
    pid_t pid ;
    if (sigsetjmp(buf,1)==0) { 
	pid = fork() ;
	if (pid == 0) {
	    setpgid(pid,pid);
	    freopen(err_file,"w",stderr) ;
	    execv(compile_cmd,argv) ;
	    exit(0) ;
	}
	sleep(max_compile_time) ;
	signal(SIGCHLD,SIG_DFL);
	kill(-pid, SIGKILL) ;
	while (waitpid(-1,0,WNOHANG) > 0) ;
	FILE* ferr = fopen(err_file,"w") ;
	fprintf(ferr,"compile error!");
	fclose(ferr);
	return  ;
    }else {
	return ;
    }
}

long convert2ms(struct timeval *tv)
{
    return (tv->tv_sec*1000000 + tv->tv_usec)/1000 ;
}

void set_cost_time(struct judge_result* jr, struct rusage* usage)
{
    long cost_time ;
    cost_time = convert2ms(&usage->ru_utime) + convert2ms(&usage->ru_stime) ;
    jr->time_ms = cost_time ;
}

int next_word(char *s, int size, FILE* fin) 
{
    //read one word, at most (size-1) bytes from stream fin, saved in s
    //first we throw away the '\t' and ' ' and '\n' and '\r' these blank char
    while(1) {
	char tmp ;
	int flag = fread(&tmp,1,1,fin) ;
	if (flag<=0) {
	    return flag ;
	}
	if (tmp==' ' || tmp=='\n' || tmp=='\r' || tmp == '\t') 
	    continue ;
	else {
	    s[0] = tmp ;
	    break ;
	}
    }
    int k = 1 ;
    while (1) {
	if(k == (size-1)) {
	    s[k] = '\0' ;
	    return k ;
	}
	int flag = fread(s+k,1,1,fin) ;
	if(flag<=0) {
	    s[k] = '\0' ; 
	    return k ;
	}
	if(s[k]==' ' || s[k]=='\n' || s[k]=='\r' || s[k]=='\t'){
	    s[k] = '\0' ;
	    return k ;
	}else k++;
    }
}

int check_answer(char *user_out, char *ans)
{
    FILE* fout = fopen(user_out,"r");
    FILE* fans = fopen(ans,"r");
    if(fout==NULL || fans==NULL) return 0 ;
    char word_out[BUF_SIZE] = {0} ;
    char word_ans[BUF_SIZE] = {0} ;
    while (1) {
	int out_flag = next_word(word_out,BUF_SIZE,fout) ;
	int ans_flag = next_word(word_ans,BUF_SIZE,fans) ;
	if (out_flag!=ans_flag) return 0 ;
	if (out_flag <= 0) return 1 ;
	if (strcmp(word_out,word_ans)!=0) return 0;
    }
}

int check_syscall_ok(int first, struct user_regs_struct *uregs) 
{
    extern int syscall_white_list[] ;
    #ifdef __x86_64__
	int sys_call = uregs->orig_rax ;
    #elif __i386__
	int sys_call = uregs->orig_eax ;
    #endif
    if (first) return 1 ;
    if (syscall_white_list[sys_call] == 1) {
	if(sys_call == SYS_open){
	    #ifdef __x86_64__
	    int open_flag = uregs->rsi ;
	    #elif __i386__
	    int open_flag = uregs->ebx ;
	    #endif
	    //check for WR
	    if ( ((open_flag & O_WRONLY) ) || ((open_flag & O_RDWR) ) ) {
		return 0 ;
	    }else return 1;	       
	}else {
	    return 0 ;
	}
    }else return 1 ;
}

void judge_exe(char *input_file,
	       char *stand_answer,
	       char *output_file,
               char *ld_path,
	       int max_cpu_time_limit,
	       int max_mem_limit,
	       struct judge_result* jr,
	       char *path,
	       char *argv[])
{
    pid_t pid ;
    int insyscall = 0 ;
    //struct user_regs_struct uregs ;
    struct user context ;
    
    pid = fork() ;

    if (pid == 0) { //child
	struct rlimit rl_cpu ;
	getrlimit(RLIMIT_CPU, &rl_cpu) ;
	rl_cpu.rlim_cur = max_cpu_time_limit ;
	setrlimit(RLIMIT_CPU, &rl_cpu) ;

	struct rlimit rl_fsize ;
	getrlimit(RLIMIT_FSIZE, &rl_fsize) ;
	rl_fsize.rlim_cur = max_output_size;
	setrlimit(RLIMIT_FSIZE, &rl_fsize) ;
	
	struct rlimit rl_as ;
	getrlimit(RLIMIT_AS, &rl_as) ;
	rl_as.rlim_cur = max_as ;
	setrlimit(RLIMIT_AS, &rl_as) ;

	freopen(input_file,"r",stdin) ;
	freopen(output_file,"w",stdout) ;

	ptrace(PTRACE_TRACEME,0,NULL,NULL) ;
	execv(path,argv) ;
    }
    else {//parent
	int status ;
        int first_sys_call = 1 ;
	ptrace(PTRACE_SYSCALL, pid, NULL, NULL) ;
        
	while (1) {
	    wait(&status) ;
	    if (WIFEXITED(status))  //normally terminated
		break;
	    else if (WIFSTOPPED(status)) {
		if (WSTOPSIG(status)==SIGTRAP) {
		    if (!insyscall) {
                        if(!first_sys_call)
                          insyscall = 1 ;
			ptrace(PTRACE_GETREGS,pid,NULL,&context.regs) ;
			if (!check_syscall_ok(first_sys_call,&context.regs)) {
			    //bad system call
			    jr->state = BAD_SYSCALL ;
                            #ifdef __x86_64__
			    jr->bad_syscall_number = context.regs.orig_rax ;
			    #elif __i386__
			    jr->bad_syscall_number = uregs.orig_eax ;
			    #endif
			    //kill process
			    kill(pid, SIGKILL) ; wait(NULL) ;
			    return ;
			}
                        if(first_sys_call) first_sys_call = 0 ;
		    }else insyscall = 0 ;
		}else if(WSTOPSIG(status) == SIGXCPU) {
		    jr->state = TLE ;
		    kill(pid,SIGKILL) ;
		    wait(NULL);
		    return ;
		}else if(WSTOPSIG(status) == SIGXFSZ){
		    jr->state = OLE ;
		    kill(pid, SIGKILL) ;
		    wait(NULL) ;
		    return ;
		}else{
		    kill(pid, SIGKILL) ;
		    wait(NULL) ;
		    jr->state = RE ;
		    return ;
		}
	    }else if (WIFSIGNALED(status)) {
		    jr->state = RE ;
		    return ;
	    }else {
		fprintf(stderr,"Unknown status: %d\n", status) ;
		return ;
	    }
	    ptrace(PTRACE_SYSCALL,pid,NULL,NULL);
	}
	struct rusage usage ;
	getrusage(RUSAGE_CHILDREN, &usage) ;
	if (usage.ru_maxrss > max_mem_limit) {
	    jr->state = MLE ;
	    return ;
	}
	//check answer
        int ac = -1;
        if (ld_path) {
          void *ld_handler = dlopen(ld_path,RTLD_LAZY) ;
          if (ld_handler) {
            void * sym_addr = NULL ;
            sym_addr = dlsym(ld_handler,"ta_check") ;
            if (sym_addr) {
              ac = ((check_function)sym_addr)(stand_answer,output_file) ;
            }
          }
        }
        if (ac<0)
          ac = check_answer(stand_answer,output_file) ;
	//remove output
	if (ac) {
	    jr->state = AC ;
	    jr->mem_kb = usage.ru_maxrss ;
	    set_cost_time(jr,&usage) ;
	    return ;
	}else {
	    jr->state = WA ;
	    return ;
	}
    }
}
