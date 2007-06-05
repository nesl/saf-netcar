#include <stdio.h>
#include <stdlib.h>
#include <math.h>


int main(int argc, char *args[]){
	float time = 0;
	float time_interval = 1/19.5;
	int  frequency = 1000;
	int  amplitude = 50;
	float height = 525;
	int value;
	FILE *fd;

	switch (argc){
		case 4: amplitude = atoi(args[3]);
		case 3: frequency = atoi(args[2]);
		case 2: fd = fopen(args[1], "w");
			break;
		default: printf("error usage: sinelong [outifle] [freq (1000 is 1 hz)] [amp]\n");
		   	 exit(1);
	}

	while (time < 2000){
		value = (int) amplitude * sin(time*2*3.14*frequency/1000.0) + height;
		fprintf(fd, "%f\t%d\t%d\n", time, value, value);
		time += time_interval;
	}

	fclose(fd);

	return 0;
}
