#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

#define PORT 5000
#define SIZE 1024

int main(int argc, char *argv[]) {
    int sock;
    struct sockaddr_in addr;
    char buffer[SIZE];

    if (argc != 3) {
        printf("Usage: %s <ON_IP> <VNS_ID>\n", argv[0]);
        return 1;
    }

    sock = socket(AF_INET, SOCK_STREAM, 0);

    if (sock < 0) {
        perror("socket");
        return 1;
    }

    addr.sin_family = AF_INET;
    addr.sin_port = htons(PORT);

    if (inet_pton(AF_INET, argv[1], &addr.sin_addr) != 1) {
        printf("Invalid ON IP address.\n");
        close(sock);
        return 1;
    }

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("connect");
        close(sock);
        return 1;
    }

    snprintf(buffer, SIZE, "Connection information from VNS %s", argv[2]);

    if (send(sock, buffer, strlen(buffer), 0) < 0) {
        perror("send");
        close(sock);
        return 1;
    }

    printf("Sent initial connection message to ON.\n");
    printf("Waiting for link-state message...\n");

    int n = recv(sock, buffer, SIZE - 1, 0);

    if (n > 0) {
        buffer[n] = '\0';
        printf("Received from ON: %s\n", buffer);
    } else if (n == 0) {
        printf("ON closed the connection.\n");
    } else {
        perror("recv");
    }

    close(sock);
    return 0;
}
