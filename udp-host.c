#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>

int s;

void *receive_messages(void *arg) {
    char buf[1024];
    struct sockaddr_in sender;
    socklen_t len;

    while (1) {
        len = sizeof(sender);
        int n = recvfrom(s, buf, sizeof(buf) - 1, 0, (struct sockaddr *)&sender, &len);

        if (n > 0) {
            buf[n] = '\0';
            printf("\nMessage from %s:%d: %s", inet_ntoa(sender.sin_addr), ntohs(sender.sin_port), buf);
            printf("\nEnter destination IP, port and message:\n");
            fflush(stdout);
        }
    }

    return NULL;
}

int main(int argc, char *argv[]) {
    struct sockaddr_in addr, dest;
    char ip[50], buf[1024];
    int port;
    pthread_t tid;

    if (argc != 3) {
        printf("Usage: %s <my_ip> <my_port>\n", argv[0]);
        return 1;
    }

    s = socket(AF_INET, SOCK_DGRAM, 0);

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[2]));
    addr.sin_addr.s_addr = inet_addr(argv[1]);

    if (bind(s, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(s);
        return 1;
    }

    printf("Host running at %s:%s\n", argv[1], argv[2]);

    pthread_create(&tid, NULL, receive_messages, NULL);

    while (1) {
        printf("\nDestination IP: ");
        fflush(stdout);

        if (scanf("%49s", ip) != 1)
            break;

        printf("Destination port: ");
        fflush(stdout);

        if (scanf("%d", &port) != 1)
            break;

        getchar();

        printf("Message: ");
        fflush(stdout);

        if (fgets(buf, sizeof(buf), stdin) == NULL)
            break;

        memset(&dest, 0, sizeof(dest));
        dest.sin_family = AF_INET;
        dest.sin_port = htons(port);
        dest.sin_addr.s_addr = inet_addr(ip);

        sendto(s, buf, strlen(buf), 0, (struct sockaddr *)&dest, sizeof(dest));
    }

    close(s);
    return 0;
}