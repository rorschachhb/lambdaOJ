#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

int main(){
	int fid = open("./test",O_RDWR);
	return 0 ;
}
