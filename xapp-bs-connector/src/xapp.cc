/*
==================================================================================

        Copyright (c) 2019-2020 AT&T Intellectual Property.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
==================================================================================
 */
/*
 * xapp.cc
 *
 *  Mar, 2020 (Shraboni Jana)
 */

#include "xapp.hpp"
#include <nlohmann/json.hpp>
#define BUFFER_SIZE 1024

using json = nlohmann::json;

std::vector<std::string> gnb_id_vector;
int agent_socket_fd = -1;

Xapp::Xapp(XappSettings &config, XappRmr &rmr, bool protobuf){

    if (protobuf) {
        std::cout << "Initialized xApp with Protobuf" << std::endl;
    }

    rmr_ref = &rmr;
    config_ref = &config;
    xapp_mutex = NULL;
    subhandler_ref = NULL;
    using_protobuf = protobuf;
    return;
}

Xapp::~Xapp(void){

    //Joining the threads
    int threadcnt = xapp_rcv_thread.size();
    for(int i=0; i<threadcnt; i++){
        if(xapp_rcv_thread[i].joinable())
            xapp_rcv_thread[i].join();
    }
    xapp_rcv_thread.clear();

    if(xapp_mutex!=NULL){
        xapp_mutex->~mutex();
        delete xapp_mutex;
    }

    // close sockets
    close_control_socket_agent();

    // join threads
    for (int i = 0; i < control_thr_rx.size(); ++i) {
        if(control_thr_rx[i] && control_thr_rx[i]->joinable()) {
            control_thr_rx[i]->join();
        }
    }

    if(ext_control_thr_rx && ext_control_thr_rx->joinable()) {
        ext_control_thr_rx->join();
    }
};

//Stop the xapp. Note- To be run only from unit test scripts.
void Xapp::stop(void){
    // Get the mutex lock
    std::lock_guard<std::mutex> guard(*xapp_mutex);
    rmr_ref->set_listen(false);
    rmr_ref->~XappRmr();

    //Detaching the threads....not sure if this is the right way to stop the receiver threads.
    //Hence function should be called only in Unit Tests
    int threadcnt = xapp_rcv_thread.size();
    for(int i=0; i<threadcnt; i++){
        xapp_rcv_thread[i].detach();
    }
    sleep(10);
}

void Xapp::startup(SubscriptionHandler &sub_ref) {

    subhandler_ref = &sub_ref;
    char* gnb_id_subscription = std::getenv("GNB_ID");

    if (gnb_id_subscription == NULL) {
        // get list of gnbs from ric
        mdclog_write(MDCLOG_INFO, "Environmental variable GNB_ID not defined\n");
        mdclog_write(MDCLOG_INFO, "Getting gNB list from RIC\n");
        set_rnib_gnblist();
    }
    else {
        // only insert target gnb
        mdclog_write(MDCLOG_INFO, "Querying target gNB %s\n", gnb_id_subscription);
        rnib_gnblist.push_back(gnb_id_subscription);
    }

    if (using_protobuf) {
        indreq_buflen = oneshot_external_control_message_udp(SOCKET_PORT_EXT_PROTOBUF, &indreq_buf);
        indreq_buf[indreq_buflen] = '\0';
        indreq_buflen += 1;

        std::cout << "Initial indication request received, bytes: " << indreq_buflen << std::endl;
    }

    // open external control socket in thread and wait for message
    ext_control_thr_rx = std::unique_ptr<std::thread>(new std::thread{&Xapp::handle_external_control_message, this, SOCKET_PORT_EXT});

    // open control socket with agent
    if (open_control_socket_agent(const_cast<char*>(AGENT_IP), 4200) == 0) {
        // start receive thread
        std::unique_ptr<std::thread> tmp_thr = std::unique_ptr<std::thread>(new std::thread{&Xapp::handle_rx_msg_agent, this, AGENT_IP});
        control_thr_rx.push_back(std::move(tmp_thr));
    }

    //send subscriptions.
    startup_subscribe_requests();

    //read A1 policies
    // startup_get_policies();

    return;
}

void Xapp::Run(){
    rmr_ref->set_listen(true);
    if(xapp_mutex == NULL){
        xapp_mutex = new std::mutex();
    }
    std::lock_guard<std::mutex> guard(*xapp_mutex);

    for(int j=0; j < _callbacks.size(); j++){
        std::thread th_recv([&](){ rmr_ref->xapp_rmr_receive(std::move(_callbacks[j]), rmr_ref);});
        xapp_rcv_thread.push_back(std::move(th_recv));
    }

    return;
}
//Starting a seperate single receiver
void Xapp::start_xapp_receiver(XappMsgHandler& mp_handler){
    //start a receiver thread. Can be multiple receiver threads for more than 1 listening port.
    rmr_ref->set_listen(true);
    if(xapp_mutex == NULL){
        xapp_mutex = new std::mutex();
    }

    mdclog_write(MDCLOG_INFO,"Receiver Thread file= %s, line=%d",__FILE__,__LINE__);
    std::lock_guard<std::mutex> guard(*xapp_mutex);
    std::thread th_recv([&](){ rmr_ref->xapp_rmr_receive(std::move(mp_handler), rmr_ref);});
    xapp_rcv_thread.push_back(std::move(th_recv));
    return;



}
void Xapp::shutdown(){
    return;
}


void Xapp::startup_subscribe_requests(void ){

    bool res;
    size_t data_size = ASN_BUFF_MAX_SIZE;
    unsigned char   data[data_size];
    unsigned char meid[RMR_MAX_MEID];
    std::string xapp_id = config_ref->operator [](XappSettings::SettingName::XAPP_ID);

    mdclog_write(MDCLOG_INFO,"Preparing to send subscription in file= %s, line=%d",__FILE__,__LINE__);

    std::string sub_id = "1";

    auto gnblist = get_rnib_gnblist();
    int sz = gnblist.size();

    if(sz <= 0)
        mdclog_write(MDCLOG_INFO,"Subscriptions cannot be sent as GNBList in RNIB is NULL");

    for(int i = 0; i<sz; i++){

        //give the message to subscription handler, along with the transmitter.
        strcpy((char*)meid,gnblist[i].c_str());

        // char *strMsg = "Subscription Request from HelloWorld XApp\0";
        // strncpy((char *)data,strMsg,strlen(strMsg));
        // data_size = strlen(strMsg);

        unsigned char buf[1024];
        size_t buf_size = 1024;


        HWEventTriggerDefinition eventObj;
        eventObj.set_triggerNature(0);

        //creating Action Definition
        HWActionDefinition e2sm_actdefn1;
        e2sm_actdefn1.add(HWActionDefinition::RANParamIEs().set_param_id(1).set_param_name("ENodeBID").set_param_test(1).set_param_value("SR123"));

        if (using_protobuf) {
            e2sm_actdefn1.add(HWActionDefinition::RANParamIEs().set_param_id(1).set_param_name("ProtobufMessage").set_param_test(1).set_param_value(indreq_buf));
        }

        //first Action Object
        E2APAction<HWActionDefinition> actionObj;
        actionObj.add(E2APAction<HWActionDefinition>::ActionIEs().set_ricActionID(1).set_ricActionType(1).set_ricActionDefinition(e2sm_actdefn1));

        E2APSubscriptionRequest<HWEventTriggerDefinition, HWActionDefinition> requestObj(E2APSubscriptionRequest<HWEventTriggerDefinition, HWActionDefinition>::SubscriptionRequestIEs().set_ranFunctionID(1).set_ricInstanceID(1).set_ricRequestorID(3).set_ricAction_ToBeSetup_List(actionObj).set_ricEventTriggerDefinition(eventObj));

        bool res = requestObj.encode(&buf[0], &buf_size);
        if(!res)
            mdclog_write(MDCLOG_ERR,"SubscriptionRequest ENCODING Error: %s",requestObj.get_error().c_str());
        else
            mdclog_write(MDCLOG_INFO,"SubscriptionRequest ENCODING SUCESS");



        xapp_rmr_header rmr_header;
        rmr_header.message_type = RIC_SUB_REQ;
        rmr_header.payload_length = buf_size; //data_size

        strcpy((char*)rmr_header.sid,sub_id.c_str());
        strcpy((char*)rmr_header.meid,gnblist[i].c_str());

        mdclog_write(MDCLOG_INFO,"Sending subscription in file= %s, line=%d for MEID %s",__FILE__,__LINE__, meid);
        auto transmitter = std::bind(&XappRmr::xapp_rmr_send,rmr_ref, &rmr_header, (void*)buf );//(void*)data);

        int result = subhandler_ref->manage_subscription_request(gnblist[i], transmitter);
        if(result==SUBSCR_SUCCESS){
            mdclog_write(MDCLOG_INFO,"Subscription SUCCESSFUL in file= %s, line=%d for MEID %s",__FILE__,__LINE__, meid);
        }
        else {
            mdclog_write(MDCLOG_ERR,"Subscription FAILED in file= %s, line=%d for MEID %s",__FILE__,__LINE__, meid);
        }
    }
}

void Xapp::startup_get_policies(void){

    int policy_id = HELLOWORLD_POLICY_ID;

    std::string policy_query = "{\"policy_type_id\":" + std::to_string(policy_id) + "}";
    unsigned char * message = (unsigned char *)calloc(policy_query.length(), sizeof(unsigned char));
    memcpy(message, policy_query.c_str(),  policy_query.length());
    xapp_rmr_header header;
    header.payload_length = policy_query.length();
    header.message_type = A1_POLICY_QUERY;
    mdclog_write(MDCLOG_INFO, "Sending request for policy id %d\n", policy_id);
    rmr_ref->xapp_rmr_send(&header, (void *)message);
    free(message);

}

void Xapp::set_rnib_gnblist(void) {

    openSdl();

    void *result = getListGnbIds();
    if(strlen((char*)result) < 1){
        mdclog_write(MDCLOG_ERR, "ERROR: no data from getListGnbIds\n");
        return;
    }

    mdclog_write(MDCLOG_INFO, "GNB List in R-NIB %s\n", (char*)result);


    Document doc;
    ParseResult parseJson = doc.Parse<kParseStopWhenDoneFlag>((char*)result);
    if (!parseJson) {
        std::cerr << "JSON parse error: %s (%u)", GetParseErrorFunc(parseJson.Code());
        return;
    }

    if(!doc.HasMember("gnb_list")){
        mdclog_write(MDCLOG_INFO, "JSON Has No GNB List Object");
        return;
    }
    assert(doc.HasMember("gnb_list"));

    const Value& gnblist = doc["gnb_list"];
    if (gnblist.IsNull())
        return;

    if(!gnblist.IsArray()){
        mdclog_write(MDCLOG_INFO, "GNB List is not an array");
        return;
    }


    assert(gnblist.IsArray());
    for (SizeType i = 0; i < gnblist.Size(); i++) // Uses SizeType instead of size_t
    {
        assert(gnblist[i].IsObject());
        const Value& gnbobj = gnblist[i];
        assert(gnbobj.HasMember("inventory_name"));
        assert(gnbobj["inventory_name"].IsString());
        std::string name = gnbobj["inventory_name"].GetString();
        rnib_gnblist.push_back(name);

    }
    closeSdl();
    return;

}


void Xapp::send_ric_control_request(char* payload, int payload_len, std::string gnb_id) {
    
    mdclog_write(MDCLOG_INFO, "Sending RIC Control Request\n");

    // std::cout << "send_ric_control_request: received Protobuf message of size " << payload_len << std::endl;
    // for(int i = 0; i < payload_len; i++) {
    //     fprintf(stderr, " %hhx ", payload[i]);
    // }
    // fprintf(stderr, "\n");

    // unsigned char meid[RMR_MAX_MEID];
    std::string xapp_id = config_ref->operator [](XappSettings::SettingName::XAPP_ID);

    mdclog_write(MDCLOG_INFO, "Preparing to send control in file= %s, line=%d", __FILE__, __LINE__);

    auto gnblist = get_rnib_gnblist();
    int sz = gnblist.size();

    if(sz <= 0) {
        mdclog_write(MDCLOG_INFO, "Subscriptions cannot be sent as GNBList in RNIB is NULL");
        return;
    }

    // give the message to subscription handler, along with the transmitter.
    // strcpy((char*)meid, gnb_id.c_str());
    mdclog_write(MDCLOG_INFO, "RIC Control Request, gNB %s\n", gnb_id.c_str());

    unsigned char buf[1024];
    size_t buf_size = 1024;

    HWControlHeader headObj;
    headObj.set_ricControlHeader(1);

    HWControlMessage msgObj;
    msgObj.set_ricControlMessage(std::string(payload, payload_len), payload_len);

    E2APControlMessage<HWControlHeader,HWControlMessage>::ControlRequestIEs infoObj;  // this refers to the e2ap_control_request.hpp
    infoObj.set_ranFunctionID(1);
    infoObj.set_ricRequestorID(1);
    infoObj.set_ricControlHeader(&headObj);
    infoObj.set_ricControlMessage(&msgObj);
    //  infoObj.set_ricCallProcessID("ProcessID");

    E2APControlMessage<HWControlHeader,HWControlMessage> cntrlObj(infoObj);  // this refers to the e2ap_control_request.hpp

    bool res = cntrlObj.encode(buf, &buf_size);
    if(!res)
        mdclog_write(MDCLOG_ERR,"ControlMessage ENCODING Error: %s\n", cntrlObj.get_error().c_str());
    else
        mdclog_write(MDCLOG_INFO,"ControlMessage ENCODING SUCESS\n");


    xapp_rmr_header rmr_header;
    rmr_header.message_type = RIC_CONTROL_REQ;
    rmr_header.payload_length = buf_size;

    // strcpy((char*)rmr_header.sid, sub_id.c_str());
    // strcpy((char*)rmr_header.meid, gnblist[i].c_str());
    strcpy((char*)rmr_header.meid, gnb_id.c_str());

    mdclog_write(MDCLOG_INFO,"Sending control in file= %s, line=%d",__FILE__,__LINE__);
    // auto transmitter = std::bind(&XappRmr::xapp_rmr_send, rmr_ref, &rmr_header, (void*)buf );

    int result = rmr_ref->xapp_rmr_send(&rmr_header, (void*)buf);
    if(result){
        mdclog_write(MDCLOG_INFO, "CTRL REQ SUCCESSFUL in file= %s, line=%d",__FILE__,__LINE__);
    }
    else {
        mdclog_write(MDCLOG_INFO, "CTRL REQ FAILED in file= %s, line=%d",__FILE__,__LINE__);
    }
}

// handle received message from a specific DRL agent
void Xapp::handle_rx_msg_agent(std::string agent_ip) {
    std::cout << "Opening RX thread with agent " << agent_ip << std::endl;

    const size_t max_size = 256;
    char buf[max_size] = {0};

    // listen to control from agent
    while (true) {
        if (agent_socket_fd > -1) {
            int rcv_size = recv(agent_socket_fd, buf, max_size, 0);
            if (rcv_size > 0) {
                std::cout << "Message from agent " << agent_ip << std::endl;
                std::cout << buf << std::endl;

                std::string gnb_id = "";
                std::string control;

                if (!using_protobuf) {
                    // get received message fields
                    json buf_json = json::parse(buf);
                    gnb_id = buf_json.value("gnb_id", "");
                    control = buf_json.value("control", "");

                    std::cout << "Received gnb_id: " << gnb_id << std::endl;
                    std::cout << "Received control: " << control << std::endl;

                    // send RIC control request
                    send_ric_control_request((char*) control.c_str(), control.length(), gnb_id);
                }
                else {
                    std::cout << "Received Protobuf message of size " << rcv_size << std::endl;
                    for(int i = 0; i < rcv_size; i++) {
                        fprintf(stderr, " %hhx ", buf[i]);
                    }
                    fprintf(stderr, "\n");

                    // TODO: potentially associate socket with gnb
                    gnb_id = gnb_id_vector.at(0);
                    std::cout << "Sending RIC control request to gNB with ID " << gnb_id << std::endl;

                    // send RIC control request
                    send_ric_control_request((char*) &buf, rcv_size, gnb_id);
                }

                memset(buf, 0, max_size);
            }
        }
    }
}

// handle external control socket message
void Xapp::handle_external_control_message(int port) {

    // Create a socket (IPv4, TCP)
    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd == -1) {
        std::cout << "Failed to create socket. errno: " << errno << std::endl;
        return;
    }

    // Listen on given port on any address
    sockaddr_in sockaddr;
    sockaddr.sin_family = AF_INET;
    sockaddr.sin_addr.s_addr = INADDR_ANY;
    sockaddr.sin_port = htons(port);

    if (bind(sockfd, (struct sockaddr*)&sockaddr, sizeof(sockaddr)) < 0) {
        std::cout << "Failed to bind to port. Errno: " << errno << std::endl;
        return;
    }

    // Start listening. Hold at most 10 connections in the queue
    if (listen(sockfd, 10) < 0) {
        std::cout << "Failed to listen on socket. Errno: " << errno << std::endl;
        return;
    }

    std::cout << "Opened control socket server on port " << port << std::endl;

    while (true) {
        auto addrlen = sizeof(sockaddr);
        int connection = accept(sockfd, (struct sockaddr*)&sockaddr, (socklen_t*)&addrlen);
        
        if (connection < 0) {
            continue;
        }

        // Read from the connection
        const size_t max_size = 256;
        char buffer[max_size] = {0};
        auto bytes_read = read(connection, buffer, 100);
        
        if (bytes_read > 0) {
            // remove newline characters
            int size_newline = std::remove(buffer, buffer + strlen(buffer), '\n') - buffer;
            buffer[size_newline] = '\0';

            std::cout << "External control socket. Message received: " << buffer << std::endl;

            // get message fields
            // example: "{\"control\": \"terminate\", \"gnb_id\": \"all\"}"
            json buffer_json = json::parse(buffer);
            std::string gnb_id = buffer_json.value("gnb_id", "");
            std::string control = buffer_json.value("control", "");

            std::cout << "Received control: " << control << std::endl;
            std::cout << "Received gnb_id: " << gnb_id << std::endl;

            // check if message is termination, send to DU and shutdown xApp
            if (control.compare(XAPP_TERMINATE) == 0) {
                if (gnb_id.length() > 0 && gnb_id.compare(TERMINATE_ALL_KEYWORD) == 0) {
                    terminate_du_reporting_all();
                }
                else if (gnb_id.length() > 0) {
                    terminate_du_reporting_single(gnb_id);
                }
                else {
                    std::cout << "No valid gNB ID passed" << std::endl;
                }
            }
            else {
                std::cout << "Received unknown message from control socket" << std::endl;
            }
        }

        memset(buffer, 0, max_size);
        close(connection);
    }

    close(sockfd);

    return;
}

// terminate all DU reportings and shutdown xApp
// after calling this function, the orchestrator should uninstall the xApp through the dms_cli command
void Xapp::terminate_du_reporting_all(void) {

    std::cout << "Terminating all gNB reportings" << std::endl;

    for (int i = 0; i < gnb_id_vector.size(); ++i) {
        std::string gnb_id = gnb_id_vector[i];
        terminate_du_reporting_single(gnb_id);
    }

    // clear vector
    gnb_id_vector.clear();
}

// terminate all DU reportings and shutdown xApp
void Xapp::terminate_du_reporting_single(std::string gnb_id) {

    std::cout << "Terminating single gNB reporting from " << gnb_id << std::endl;
    send_ric_control_request(XAPP_TERMINATE, strlen(XAPP_TERMINATE), gnb_id);

    // remove gnb_id from vector
    std::vector<std::string>::iterator it;
    for (it = gnb_id_vector.begin(); it != gnb_id_vector.end(); ++it) {
        if(gnb_id.compare(*it) == 0) {
            gnb_id_vector.erase(it);
            std::cout << "Removed " << gnb_id << " from data structure" << std::endl;
            break;
        }
    }
}

// handle external control socket message
int Xapp::oneshot_external_control_message_udp(int port, char** buffer) {

    // Create a socket (IPv4, TCP)
    int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd == -1) {
        std::cout << "Failed to create socket. errno: " << errno << std::endl;
        return 0;
    }

    // Listen on given port on any address
    sockaddr_in socket_listen_addr;
    socket_listen_addr.sin_family = AF_INET;
    socket_listen_addr.sin_addr.s_addr = INADDR_ANY;
    socket_listen_addr.sin_port = htons(port);

    if (bind(sockfd, (struct sockaddr*) &socket_listen_addr, sizeof(socket_listen_addr)) < 0) {
        std::cout << "Failed to bind to port. Errno: " << errno << std::endl;
        return 0;
    }

    std::cout << "Opened control socket server on port " << port << std::endl;
    
    // Read from the connection
    const size_t max_size = 256;
    *buffer = (char*) calloc(max_size, sizeof(char));
    unsigned int socket_listen_addr_len = sizeof(socket_listen_addr);
    int revclen = recvfrom(sockfd, *buffer, max_size, MSG_WAITALL, (struct sockaddr*) &socket_listen_addr, (socklen_t*) &socket_listen_addr_len);
    if(revclen < 0){
        std::cout << "Error receiving message from conrol socket" << std::endl;
    }
    close(sockfd);
    std::cout << "exiting oneshot receiver, received: " << revclen << std::endl;
    return revclen;
}

