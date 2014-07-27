#include <stdio.h>
#include <stdlib.h>
int a[1024][1024][10] ;
int main(){
	char *p ;
	p = malloc(1024*1024*40) ;
	int i ;
	for(i=0;i<1024*1024*39;i++) p[i] = 'a' ;
}
