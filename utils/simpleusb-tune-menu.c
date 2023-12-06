/*
 * Asterisk -- An open source telephony toolkit.
 *
 * Copyright (C) 2010, Jim Dixon, WB6NIL
 *
 * Jim Dixon <jim@lambdatel.com>
 *
 * See http://www.asterisk.org for more information about
 * the Asterisk project. Please do not directly contact
 * any of the maintainers of this project for assistance;
 * the project provides a web site, mailing lists and IRC
 * channels for your use.
 *
 * This program is free software, distributed under the terms of
 * the GNU General Public License Version 2. See the LICENSE file
 * at the top of the source tree.
 */

/*
 *
 * Usbsusb tune menu program
 *
 */
 
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <ctype.h>
#include <signal.h>
#include <errno.h>  
#include <sys/wait.h>

static void ourhandler(int sig)
{
int	i;

	signal(sig,ourhandler);
	while(waitpid(-1, &i, WNOHANG) > 0);
	return;
}


static int qcompar(const void *a, const void *b)
{
char **sa = (char **)a,**sb =(char **)b;

	return(strcmp(*sa,*sb));
}

/*
* Break up a delimited string into a table of substrings
*
* str - delimited string ( will be modified )
* strp- list of pointers to substrings (this is built by this function), NULL will be placed at end of list
* limit- maximum number of substrings to process
* delim- user specified delimeter
* quote- user specified quote for escaping a substring. Set to zero to escape nothing.
*
* Note: This modifies the string str, be suer to save an intact copy if you need it later.
*
* Returns number of substrings found.
*/

static int explode_string(char *str, char *strp[], int limit, char delim, char quote)
{
int     i,l,inquo;

        inquo = 0;
        i = 0;
        strp[i++] = str;
        if (!*str)
           {
                strp[0] = 0;
                return(0);
           }
        for(l = 0; *str && (l < limit) ; str++)
        {
		if(quote)
		{
                	if (*str == quote)
                   	{	
                        	if (inquo)
                           	{
                                	*str = 0;
                                	inquo = 0;
                           	}
                        	else
                           	{
                                	strp[i - 1] = str + 1;
                                	inquo = 1;
                           	}
			}
		}	
                if ((*str == delim) && (!inquo))
                {
                        *str = 0;
			l++;
                        strp[i++] = str + 1;
                }
        }
        strp[i] = 0;
        return(i);

}

/* for a process running 'aserisk -rx' to do a remote command
   and open a pipe and a descriptor of our side of the pipe,
   or -1 if error */
static int doastcmd(char *cmd)
{
int	pfd[2],pid,nullfd;

	if (pipe(pfd) == -1)
	{
		perror("Error: cannot open pipe");
		return -1;
	}
	if (fcntl(pfd[0],F_SETFL,O_NONBLOCK) == -1)
	{
		perror("Error: cannot set pipe to NONBLOCK");
		return -1;
	}
	nullfd = open("/dev/null",O_RDWR);
	if (nullfd == -1)
	{
		perror("Error: cannot open /dev/null");
		return -1;
	}
	pid = fork();
	if (pid == -1)
	{
		perror("Error: cannot fork");
		return -1;
	}
	if (pid)  /* if this is us (the parent) */
	{
		close(pfd[1]);
		return(pfd[0]);
	}
	close(pfd[0]);
	if (dup2(nullfd,fileno(stdin)) == -1)
	{
		perror("Error: cannot dup2() stdin");
		exit(0);
	}
	if (dup2(pfd[1],fileno(stdout)) == -1)
	{
		perror("Error: cannot dup2() stdout");
		exit(0);
	}
	if (dup2(pfd[1],fileno(stderr)) == -1)
	{
		perror("Error: cannot dup2() stderr");
		exit(0);
	}
	execl("/usr/sbin/asterisk","asterisk","-rx",cmd,NULL);
	exit(0);
}

/* check to see if fd1 (or fd2, if specified) is ready to read.
   returns -1 if error, 0 if nothing ready, or ready fd + 1
   (akward, but needed to support having an fd of 0, which
   is likely, since thats most likely stdin), specify
   fd2 as -1 if not used */
static int waitfds(int fd1,int fd2,int ms)
{
fd_set fds;
struct timeval tv;
int	i,r;

	FD_ZERO(&fds);
	FD_SET(fd1,&fds);
	if (fd2 >= 0) FD_SET(fd2,&fds);
	tv.tv_usec = ms * 1000;
	tv.tv_sec = 0;
	i = fd1;
	if (fd2 > fd1) i = fd2;
	r = select(i + 1,&fds,NULL,NULL,&tv);
	if (r < 1) return(r);
	if (FD_ISSET(fd1,&fds)) return(fd1 + 1);
	if ((fd2 > 0) && (FD_ISSET(fd2,&fds))) return(fd2 + 1);
	return(0);	
}

/* get a character from an fd */
static int getcharfd(int fd)
{
char	c;

	if (read(fd,&c,1) != 1) return -1;
	return(c);
}

/* get a string from an fd */
static int getstrfd(int fd,char *str, int max)
{
int	i,j;
char	c;

	i = 0;
	for(i = 0; (i < max) || (!max); i++)
	{
		do 
		{
			j = waitfds(fd,-1,100);
			if (j == -1) 
			{
				if (errno != EINTR) return(0);
				j = 0;
			}
		}
		while (!j);
		j = read(fd,&c,1);
		if (j == 0) break;
		if (j == -1)
		{
			if (errno == EINTR) continue;
			break;
		}
		if (c == '\n') break;
		if (str) str[i] = c;
	}
	if (str) str[i] = 0;
	return(i);
}

/* get 1 line of data from Asterisk */
static int astgetline(char *cmd, char *str, int max)
{
int	fd,rv;

	fd = doastcmd(cmd);
	if (fd == -1) 
	{
		perror("Error getting data from Asterisk");
		return(-1);
	}
	rv = getstrfd(fd,str,max);
	close(fd);
	if (rv > 0) return(0);
	return(1);
}

/* get repsonse from Asterisk and output to stdout */
static int astgetresp(char *cmd)
{
int	i,w,fd;
char	str[256];

	fd = doastcmd(cmd);
	if (fd == -1) 
	{
		perror("Error getting response from Asterisk");
		return(-1);
	}
	for(;;)
	{	
		w = waitfds(fileno(stdin),fd,100);
		if (w == -1) 
		{
			if (errno == EINTR) continue;
			perror("Error processing response from Asterisk");
			close(fd);
			return(-1);
		}
		if (!w) continue;
		/* if its our console */
		if (w == (fileno(stdin) + 1))
		{
			getstrfd(fileno(stdin),str,sizeof(str) - 1);
			break;
		}
		/* if its Asterisk */
		if (w == (fd + 1))
		{
			i = getcharfd(fd);
			if (i == -1) break;
			putchar(i);
			fflush(stdout);
			continue;
		}
	}
	close(fd);
	return(0);
}

static void menu_selectusb(void)
{
int	i,n,x;
char	str[100],buf[256],*strs[100];

	printf("\n");
	/* print selected USB device */
	if (astgetresp("susb active")) return;
	/* get device list from Asterisk */
	if (astgetline("susb tune menu-support 1",buf,sizeof(buf) - 1)) exit(255);
	n = explode_string(buf,strs,100,',',0);
	if (n < 1)
	{
		fprintf(stderr,"Error parsing USB device information\n");
		return;
	}
	qsort(strs,n,sizeof(char *),qcompar);
	printf("Please select from the following USB devices:\n");
	for (x = 0; x < n; x++)
	{
		printf("%d) Device [%s]\n",x + 1,strs[x]);
	}
	printf("0) Exit Selection\n");
	printf("Enter make your selection now: ");
	if (fgets(str,sizeof(str) - 1,stdin) == NULL)
	{
		printf("USB device not changed\n");
		return;
	}
	if (str[0] && (str[strlen(str) - 1] == '\n'))
		str[strlen(str) - 1] = 0;
	for(x = 0; str[x]; x++)
	{
		if (!isdigit(str[x])) break;
	}
	if (str[x] || (sscanf(str,"%d",&i) < 1) || (i < 0) || (i > n))
	{
		printf("Entry Error, USB device not changed\n");
		return;
	}
	if (i < 1)
	{
		printf("USB device not changed\n");
		return;
	}
	snprintf(str,sizeof(str) - 1,"susb active %s",strs[i - 1]);
	astgetresp(str);
	return;
}

static void menu_swapusb(void)
{
int	i,n,x;
char	str[100],buf[256],*strs[100];

	printf("\n");
	/* print selected USB device */
	if (astgetresp("susb active")) return;
	/* get device list from Asterisk */
	if (astgetline("susb tune menu-support 3",buf,sizeof(buf) - 1)) exit(255);
	n = explode_string(buf,strs,100,',',0);
	if ((n < 1) || (!*strs[0]))
	{
		fprintf(stderr,"No additional USB devices found\n");
		return;
	}
	qsort(strs,n,sizeof(char *),qcompar);
	printf("Please select from the following USB devices:\n");
	for (x = 0; x < n; x++)
	{
		printf("%d) Device [%s]\n",x + 1,strs[x]);
	}
	printf("0) Exit Selection\n");
	printf("Enter make your selection now: ");
	if (fgets(str,sizeof(str) - 1,stdin) == NULL)
	{
		printf("USB device not changed\n");
		return;
	}
	if (str[0] && (str[strlen(str) - 1] == '\n'))
		str[strlen(str) - 1] = 0;
	for(x = 0; str[x]; x++)
	{
		if (!isdigit(str[x])) break;
	}
	if (str[x] || (sscanf(str,"%d",&i) < 1) || (i < 0) || (i > n))
	{
		printf("Entry Error, USB device not swapped\n");
		return;
	}
	if (i < 1)
	{
		printf("USB device not swapped\n");
		return;
	}
	snprintf(str,sizeof(str) - 1,"susb tune swap %s",strs[i - 1]);
	astgetresp(str);
	return;
}

static void menu_rxvoice(void)
{
int	i,x;
char	str[100];

	for(;;)
	{
		if (astgetresp("susb tune menu-support b")) break;
		if (astgetresp("susb tune menu-support c")) break;
		printf("Enter new value (0-999, or CR for none): ");
		if (fgets(str,sizeof(str) - 1,stdin) == NULL)
		{
			printf("Rx voice setting not changed\n");
			return;
		}
		if (str[0] && (str[strlen(str) - 1] == '\n'))
			str[strlen(str) - 1] = 0;
		if (!str[0])
		{
			printf("Rx voice setting not changed\n");
			return;
		}
		for(x = 0; str[x]; x++)
		{
			if (!isdigit(str[x])) break;
		}
		if (str[x] || (sscanf(str,"%d",&i) < 1) || (i < 0) || (i > 999))
		{
			printf("Entry Error, Rx voice setting not changed\n");
			continue;
		}
		sprintf(str,"susb tune menu-support c%d",i);
		if (astgetresp(str)) break;
	}
	return;
}

static void menu_txa(int keying)
{
char	str[100];
int	i,x;

	if (astgetresp("susb tune menu-support f")) return;
	printf("Enter new Tx A Level setting (0-999, or C/R for none): ");
	if (fgets(str,sizeof(str) - 1,stdin) == NULL)
	{
		printf("Tx A Level setting not changed\n");
		if (keying) astgetresp("susb tune menu-support fK");
		return;
	}
	if (str[0] && (str[strlen(str) - 1] == '\n'))
		str[strlen(str) - 1] = 0;
	if (!str[0])
	{
		printf("Tx A Level setting not changed\n");
		if (keying) astgetresp("susb tune menu-support fK");
		return;
	}
	for(x = 0; str[x]; x++)
	{
		if (!isdigit(str[x])) break;
	}
	if (str[x] || (sscanf(str,"%d",&i) < 1) || (i < 0) || (i > 999))
	{
		printf("Entry Error, Tx A Level setting not changed\n");
		return;
	}
	if (keying)
		sprintf(str,"susb tune menu-support fK%d",i);
	else
		sprintf(str,"susb tune menu-support f%d",i);
	astgetresp(str);
	return;
}

static void menu_txb(int keying)
{
char	str[100];
int	i,x;

	if (astgetresp("susb tune menu-support g")) return;
	printf("Enter new Tx B Level setting (0-999, or C/R for none): ");
	if (fgets(str,sizeof(str) - 1,stdin) == NULL)
	{
		printf("Tx B Level setting not changed\n");
		if (keying) astgetresp("susb tune menu-support gK");
		return;
	}
	if (str[0] && (str[strlen(str) - 1] == '\n'))
		str[strlen(str) - 1] = 0;
	if (!str[0])
	{
		printf("Tx B Level setting not changed\n");
		if (keying) astgetresp("susb tune menu-support gK");
		return;
	}
	for(x = 0; str[x]; x++)
	{
		if (!isdigit(str[x])) break;
	}
	if (str[x] || (sscanf(str,"%d",&i) < 1) || (i < 0) || (i > 999))
	{
		printf("Entry Error, Tx B Level setting not changed\n");
		return;
	}
	if (keying)
		sprintf(str,"susb tune menu-support gK%d",i);
	else
		sprintf(str,"susb tune menu-support g%d",i);
	astgetresp(str);
	return;
}

int main(int argc, char *argv[])
{
int	flatrx = 0,txhasctcss = 0,keying = 0,echomode = 0;
char	str[256];

	signal(SIGCHLD,ourhandler);
	for(;;)
	{
		/* get device parameters from Asterisk */
		if (astgetline("susb tune menu-support 0",str,sizeof(str) - 1)) exit(255);
		if (sscanf(str,"%d,%d,%d",&flatrx,&txhasctcss,&echomode) != 3)
		{
			fprintf(stderr,"Error parsing device parameters\n");
			exit(255);
		}
		printf("\n");
		/* print selected USB device */
		if (astgetresp("susb active")) break;
		printf("1) Select USB device\n");
		printf("2) Set Rx Voice Level (using display)\n");
		if (keying)
			printf("3) Set Transmit A Level and send test tone\n");
		else
			printf("3) Set Transmit A Level\n");
		if (keying)
			printf("4) Set Transmit B Level and send test tone\n");
		else
			printf("4) Set Transmit B Level\n");
		printf("E) Toggle Echo Mode (currently %s)\n",(echomode) ? "Enabled" : "Disabled");
		printf("F) Flash (Toggle PTT and Tone output several times)\n");
		printf("P) Print Current Parameter Values\n");
		printf("S) Swap Current USB device with another USB device\n");
		printf("T) Toggle Transmit Test Tone/Keying (currently %s)\n",
			(keying) ? "Enabled" : "Disabled");
		printf("W) Write (Save) Current Parameter Values\n");
		printf("0) Exit Menu\n");
		printf("\nPlease enter your selection now: ");
		if (fgets(str,sizeof(str) - 1,stdin) == NULL) break;
		if (strlen(str) != 2) /* its 2 because of \n at end */
		{
			printf("Invalid Entry, try again\n");
			continue;
		}
		/* if to exit */
		if (str[0] == '0') break;
		switch(str[0])
		{
		    case '1':
			menu_selectusb();
			break;
		    case '2':
			menu_rxvoice();
			break;
		    case '3':
			menu_txa(keying);
			break;
		    case '4':
			menu_txb(keying);
			break;
		    case 'e':
		    case 'E':
			if (echomode)
			{
				if (astgetresp("susb tune menu-support k0")) exit(255);
			}
			else
			{
				if (astgetresp("susb tune menu-support k1")) exit(255);
			}
			break;
		    case 'f':
		    case 'F':
			if (astgetresp("susb tune menu-support l")) exit(255);
			break;
		    case 'p':
		    case 'P':
			if (astgetresp("susb tune menu-support 2")) exit(255);
			break;
		    case 's':
		    case 'S':
			menu_swapusb();
			break;
		    case 'w':
		    case 'W':
			if (astgetresp("susb tune menu-support j")) exit(255);
			break;
		    case 't':
		    case 'T':
			keying = !keying;
			printf("Transmit Test Tone/Keying is now %s\n",
				(keying) ? "Enabled" : "Disabled");
			break;
		    default:
			printf("Invalid Entry, try again\n");
			break;
		}
	}
	exit(0);
}
