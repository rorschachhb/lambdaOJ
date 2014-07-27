#include <sys/resource.h>
#include <sys/ptrace.h>
#include <sys/reg.h>
#include <sys/user.h>
#include <sys/syscall.h>
#include <syslog.h>
#include "csapp.h"
#include "hiredis/hiredis.h"

#define INIT_ERR_SIZE 4096
#define C_COMPILER "/usr/bin/gcc"
#define CPP_COMPILER "/usr/bin/g++"
#define PY_COMPILER "/usr/bin/python_compiler"
#define PYTHON "/usr/bin/python"

enum judge_state {AC=0, WA, TLE, MLE, RE, CE, BAD_SYSCALL,OLE};
enum lang {C=0,CPP,PY} ;

struct judge_result {
    enum judge_state state ;
    long time_ms ;
    long mem_kb ;
    int bad_syscall_number ;
} ;

struct lang_config {
    char* compile_cmd ;
    char* compile_args[16] ;
    char* exe_cmd ;
    char* exe_args[16] ;
} ;

extern char* state_string[];

void init_lang_config();
int copy_string_array(redisReply*,char*[]);
int next_word(char *s, int size, FILE* fin) ;
void set_compile_option(struct lang_config*,enum lang,char*) ;
void set_exe_option(struct lang_config*,enum lang,char *);
void compile_term(int sig) ;
void compile_code(char *,char *argv[],char*);
long convert2ms(struct timeval *tv) ;
void set_cost_time(struct judge_result* jr, struct rusage* usage) ;
int check_answer(char *f1, char *f2) ;
int check_syscall_ok(struct user_regs_struct *uregs) ;
void judge_exe(char *,char *, char *,int, int, struct judge_result*,char *, char *[]);
