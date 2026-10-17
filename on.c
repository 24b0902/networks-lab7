
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <time.h>

#define PORT 5000
#define EXPECTED_CLIENTS 3
#define SIZE 1024


typedef struct {
    char ip[INET_ADDRSTRLEN];
    int udp_port;
} VNInfo;

int read_file(const char* filename, int costs[EXPECTED_CLIENTS][EXPECTED_CLIENTS]){
    FILE *file = fopen(filename, "r");
    if(!file){
        perror("file not opening");
        return -1;
    }
    
    char line[SIZE];
    int row=0;

    while(fgets(line,sizeof(line),file)){
        if(line[0]=='#' || line[0]=='\n' || line[0]=='\r'){
            continue;
        }
        int col = row+1;
        char *cost = strtok(line, " \t\n\r");

        while(cost!=NULL){
            costs[row][col]=atoi(cost);
            costs[col][row]=atoi(cost);
            col++;
            cost=strtok(NULL, " \t\n\r");
        }
        row++;
    }
    fclose(file);
    if(row<=0){
        printf("No valid data in file.\n");
        return -1;
    }
    return 0;
}

void send_ls_msgs(int clients[], VNInfo vn_info[], int costs[EXPECTED_CLIENTS][EXPECTED_CLIENTS]){
    for(int i=0;i<EXPECTED_CLIENTS; i++){
        char msg[SIZE];
        int offset=0;

        for(int j=0;j<EXPECTED_CLIENTS;j++){
            if(i==j || costs[i][j]>0){

                char node_name = 'A'+j;
                msg[offset++]=node_name;

                struct in_addr ip_addr;
                inet_pton(AF_INET, vn_info[j].ip, &ip_addr);
                uint32_t s_addr = ip_addr.s_addr;
                memcpy(msg+offset, &s_addr, sizeof(s_addr));
                offset+=sizeof(s_addr);

                uint16_t udp_port = htons(vn_info[j].udp_port);
                memcpy(msg+offset, &udp_port, sizeof(udp_port));
                offset+=sizeof(udp_port);

                int32_t cost = htonl(costs[i][j]);
                memcpy(msg+offset, &cost, sizeof(cost));
                offset+=sizeof(cost);
            }
        }
        if(send(clients[i], msg, offset, 0)<0){
            perror("could not send link-state message");
        }else{
            printf("Sent link-state message to VNS %c\n", 'A'+i);
        }
    }
}

int main(int argc, char* argv[]) {
    if(argc!=2){
        printf("Usage: %s <config_file> \n", argv[0]);
        return 1;
    }


    int server, clients[EXPECTED_CLIENTS];
    struct sockaddr_in addr;
    socklen_t len = sizeof(addr);
    VNInfo vn_info[EXPECTED_CLIENTS];
    int costs[EXPECTED_CLIENTS][EXPECTED_CLIENTS]={0};

    int num = read_file(argv[1], costs);
    if(num<0){
        fprintf(stderr, "Error reading config file or empty.\n");
        return 1;
    }

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
        char buffer[SIZE];
        int n = recv(clients[i], buffer, SIZE - 1, 0);

        if (n <= 0) {
            printf("VNS %d disconnected or sent no message.\n", i + 1);
            close(clients[i]);
            close(server);
            return 1;
        }

        struct in_addr client_addr;
        memcpy(&client_addr, buffer, 4);
        inet_ntop(AF_INET, &client_addr, vn_info[i].ip, sizeof(vn_info[i].ip));

        uint16_t client_port;
        memcpy(&client_port, buffer + 4, 2);
        vn_info[i].udp_port=ntohs(client_port);

        buffer[n] = '\0';
        printf("VNS %c connected. IP: %s, UDP Port: %d\n", 'A' + i , vn_info[i].ip, vn_info[i].udp_port);
    }

    printf("\nAll VNS connection messages received.\n");
    printf("Sending link-state messages...\n");

    send_ls_msgs(clients, vn_info, costs);

    struct stat file_stat;
    time_t last_modified=0;

    if(stat(argv[1],&file_stat)==0){
        last_modified=file_stat.st_mtime;
    }
    while(1){
        sleep(20);
        if(stat(argv[1],&file_stat)==0){
            if(file_stat.st_mtime!=last_modified){
                last_modified=file_stat.st_mtime;
                printf("Config file changed. Reading new costs...\n");
                int num=read_file(argv[1], costs);
                if(num<0){
                    fprintf(stderr, "Error reading config file or empty.\n");
                    continue;
                }
                send_ls_msgs(clients, vn_info, costs);

            }
        }
    }
    for (int i = 0; i < EXPECTED_CLIENTS; i++)
        close(clients[i]);

    close(server);
    return 0;
}

