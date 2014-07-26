#include <stdio.h>
#include <stdlib.h>
int main(){
	FILE* fout = fopen("/tmp/test","w") ;
	fprintf(fout,"asdsa");
	return 0 ;
}
