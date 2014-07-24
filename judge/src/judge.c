#include "judge.h"

#define REDIS_IP "127.0.0.1"
#define REDIS_PORT 6379

int syscall_white_list[512] ; 
static sigjmp_buf buf ;
static int max_compile_time = 5;
static int max_output_size = 1024;

static char* support_language[]={"C","C++","Python2.7"};//match enum order
char* state_string[]={"Accepted","Wrong Answer","Time Limit Exceeded","Memory Limit Exceeded","Runtime Error","Compilation Error","Banned Syscall","Output Limit Exceeded"}; //match enum

redisReply* compiler[PY+1] ; //
redisReply* execute[PY+1] ;
redisReply* compile_args[PY+1] ;
redisReply* execute_args[PY+1] ;

void init_lang_config()
{
    redisContext *r = redisConnect(REDIS_IP,REDIS_PORT) ;
    if (r==NULL) {
	unix_error("redis connect error!") ;
	exit(127) ;
    }
    int i ;
    for(i=0;i<=PY;i++){
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
    wait(NULL) ;
    siglongjmp(buf,1) ;
}

void compile_code(char *compile_cmd,char *argv[],char *err_file)
{
    signal(SIGCHLD,compile_term) ;
    if (sigsetjmp(buf,1)==0) { 
	pid_t pid ;
	pid = fork() ;
	if (pid == 0) {
	    freopen(err_file,"w",stderr) ;
	    execv(compile_cmd,argv) ;
	}
	sleep(max_compile_time) ;
	signal(SIGCHLD,SIG_DFL);
	kill(pid, SIGKILL) ;
	wait(NULL) ;
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

int check_answer(char *f1, char *f2)
{
    
    return 1 ;
}

int check_syscall_ok(struct user_regs_struct *uregs) 
{
    extern int syscall_white_list[] ;
    #ifdef __x86_64__
	int sys_call = uregs->orig_rax ;
    #elif __i386__
	int sys_call = uregs->orig_eax ;
    #endif
    if (syscall_white_list[sys_call] == 1) {
	if(sys_call == SYS_open){
	    #ifdef __x86_64__
	    int open_flag = uregs->rbx ;
	    #elif __i386__
	    int open_flag = uregs->ebx ;
	    #endif
	    //check for WR
	    if ( ((open_flag & O_WRONLY) == 1) ||
		 ((open_flag & O_RDWR) == 1) ) {
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
	       int max_cpu_time_limit,
	       int max_mem_limit,
	       struct judge_result* jr,
	       char *path,
	       char *argv[])
{
    pid_t pid ;
    int insyscall = 0 ;
    struct user_regs_struct uregs ;
    
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
	
	freopen(input_file,"r",stdin) ;
	freopen(output_file,"w",stdout) ;

	ptrace(PTRACE_TRACEME,0,NULL,NULL) ;
	execv(path,argv) ;
    }
    else {//parent
	int status ;
	ptrace(PTRACE_SYSCALL, pid, NULL, NULL) ;
	
	while (1) {
	    wait(&status) ;
	    if (WIFEXITED(status))  //normally terminated
		break;
	    else if (WIFSTOPPED(status)) {
		if (WSTOPSIG(status) == SIGTRAP) {
		    if (!insyscall) {
			insyscall = 1 ;
			ptrace(PTRACE_GETREGS,pid,NULL,&uregs) ;
			if (!check_syscall_ok(&uregs)) {
			    //bad system call
			    jr->state = BAD_SYSCALL ;
                            #ifdef __x86_64__
			    jr->bad_syscall_number = uregs.orig_rax ;
			    #elif __i386__
			    jr->bad_syscall_number = uregs.orig_eax ;
			    #endif
			    //kill process
			    kill(pid, SIGKILL) ; wait(NULL) ;
			    return ;
			}
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
	int ac = check_answer(stand_answer,output_file) ;
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
