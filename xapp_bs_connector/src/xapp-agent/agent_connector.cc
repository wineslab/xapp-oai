#include "agent_connector.hpp"


// open client of control socket with agent
int open_control_socket_agent(const char* dest_ip, const int dest_port) {

  std::cout << "Opening control socket with host " << dest_ip << ":" << dest_port << std::endl;

  int control_sckfd = socket(AF_INET, SOCK_STREAM, 0);
  if (control_sckfd < 0) {
	  std::cout << "ERROR: OPEN SOCKET" << std::endl;
      close(control_sckfd);
      return -1;
  }

  // SET SOCKET OPTIONS TO RELEASE THE SOCKET ADDRESS IMMEDIATELY AFTER
  // THE SOCKET IS CLOSED
  int option(1);
  setsockopt(control_sckfd, SOL_SOCKET, SO_REUSEADDR, (char*)&option, sizeof(option));

  struct sockaddr_in dest_addr = {0};
  dest_addr.sin_family = AF_INET;
  dest_addr.sin_port = htons(dest_port);

  // convert dest_ip from char* to network address
  if (inet_pton(AF_INET, dest_ip, &dest_addr.sin_addr) <= 0) {
      std::cout << "ERROR CONVERTING IP TO INTERNET ADDR" << std::endl;
      close(control_sckfd); // if conversion fail, close the socket and return error -2
      return -2;
  }

  if (connect(control_sckfd, (struct sockaddr *) &dest_addr, sizeof(dest_addr)) < 0) {
      std::cout << "ERROR: CONNECT" << std::endl;
      close(control_sckfd);
      return -3;
  }

  // update map
  std::string agent_ip;
  agent_ip.assign(dest_ip);
  std::cout << "Agent IP " << agent_ip << std::endl;
  agent_socket_fd = control_sckfd;

  return 0;
}


// close control sockets
void close_control_socket_agent(void) {

  std::cout << "Closing control sockets with agent(s)" << std::endl;

  if (agent_socket_fd > -1) {
    close(agent_socket_fd);
  }

  // reset value
  agent_socket_fd = -1;
}


// find agent IP of socket to use with gNB id
void add_gnb_to_vector_unique(unsigned char* gnb_id_trans) {

  std::vector<std::string>::iterator it_gnb;

  // convert transaction identifier (unsigned char*) to string
  std::string gnb_id(reinterpret_cast<char*>(gnb_id_trans));

  // check if gnb_id is in vector and insert it if not present
  for (it_gnb = gnb_id_vector.begin(); it_gnb != gnb_id_vector.end(); ++it_gnb) { ; }

  // insert gnb_id into vector if not already present
  if (it_gnb == gnb_id_vector.end()) {
    gnb_id_vector.push_back(gnb_id);
    std::cout << "Added gNB ID " << gnb_id << " to data structure" << std::endl;
  }
}


// send through socket
int send_socket(const char* buf, int buf_len) {

  std::cout << "send_socket: sending data of size " << buf_len << std::endl;
  for(int i = 0; i < buf_len; i++) {
    fprintf(stderr, " %hhx ", buf[i]);
  }
  fprintf(stderr, "\n");

  if (agent_socket_fd == -1) {
    std::cout << "ERROR: Could not find socket for destination " << std::endl;
    return -1;
  }

  // const size_t max_size = 512;
  // char buf[max_size] = "Hello, Server!";  // store the data in a buffer
  // size_t data_size = strlen(buf);
  int sent_size = send(agent_socket_fd, buf, buf_len, 0);

  if(sent_size < 0) { // the send returns a size of -1 in case of errors
      std::cout <<  "ERROR: SEND to agent " << std::endl;
      return -2;
  }
  else {
      std::cout << "Message sent: " << buf << std::endl;
  }

  return 0;
}
