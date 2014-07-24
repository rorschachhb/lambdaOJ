#include <stdio.h>
int a[2000][2000] = {1} ;
int main(){
	int i,j;
	for(i=0;i<2000;i++)
	{
		for(j=0;j<2000;j++)
			a[i][j] = i+j;
	}
	return 0 ;
}
