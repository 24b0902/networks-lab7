
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

#define PORT 4559
#define EXPECTED_CLIENTS 3
#define SIZE 1024

int main() {
    int server, clients[EXPECTED_CLIENTS];
    struct sockaddr_in addr;
    socklen_t len = sizeof(addr);
    char buffer[SIZE];

    server = socket(AF_INET, SOCK_STREAM, 0);

    if (server < 0) {
        perror("socket");
        return 1;
    }

    int opt = 1;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    addr.sin_family = AF_INET;
    addr.sin_port = htons(PORT);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(server, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(server);
        return 1;
    }

    if (listen(server, EXPECTED_CLIENTS) < 0) {
        perror("listen");
        close(server);
        return 1;
    }

    printf("ON waiting for %d VNS clients...\n", EXPECTED_CLIENTS);


    for (int i = 0; i < EXPECTED_CLIENTS; i++) {
        clients[i] = accept(server, (struct sockaddr *)&addr, &len);

        if (clients[i] < 0) {
            perror("accept");
            close(server);
            return 1;
        }

        printf("VNS %d connected.\n", i + 1);

        int n = recv(clients[i], buffer, SIZE - 1, 0);

        if (n <= 0) {
            printf("VNS %d disconnected or sent no message.\n", i + 1);
            close(clients[i]);
            close(server);
            return 1;
        }

        buffer[n] = '\0';
        printf("VNS %d: %s\n", i + 1, buffer);
    }

    printf("\nAll VNS connection messages received.\n");
    printf("Sending link-state messages...\n");

   
    for (int i = 0; i < EXPECTED_CLIENTS; i++) {
        snprintf(buffer, SIZE, "Link-state message for VNS %d", i + 1);

        if (send(clients[i], buffer, strlen(buffer), 0) < 0) {
            perror("send");
        } else {
            printf("Sent to VNS %d: %s\n", i + 1, buffer);
        }
    }

    for (int i = 0; i < EXPECTED_CLIENTS; i++)
        close(clients[i]);

    close(server);
    return 0;
}

