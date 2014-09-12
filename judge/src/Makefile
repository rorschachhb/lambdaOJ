lambdajudge : judge.o main.o csapp.o cJSON.o
	gcc judge.o main.o csapp.o cJSON.o -lm -lpthread -lhiredis -ldl -o lambdajudge 
judge.o : judge.h judge.c csapp.h
	gcc -c judge.c
csapp.o : csapp.h csapp.c
	gcc -c csapp.c
cJSON.o : cJSON.h cJSON.c
	gcc -c cJSON.c
main.o : main.c csapp.h judge.h cJSON.h
	gcc -c main.c
clean : 
	rm -f *.o lambdajudge
