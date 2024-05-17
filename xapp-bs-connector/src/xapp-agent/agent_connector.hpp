

#ifndef AGENT_CONNECTOR_HPP_
#define AGENT_CONNECTOR_HPP_

#include <iostream>
#include <string.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <map>
#include <vector>

#define AGENT_IP "127.0.0.1"

// agent socket file descriptor
extern int agent_socket_fd;

// vector containing subscribed gNB IDs
extern std::vector<std::string> gnb_id_vector;

int open_control_socket_agent(const char* dest_ip, const int dest_port);
void close_control_socket_agent(void);
void add_gnb_to_vector_unique(unsigned char* gnb_id);
int send_socket(const char* buf, int buf_len);

#endif
