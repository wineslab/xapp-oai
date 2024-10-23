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
 *//*
 * xapp.hpp
 *
 *  Mar, 2020 (Shraboni Jana)
 *
 */

#pragma once

#ifndef SRC_XAPP_HPP_
#define SRC_XAPP_HPP_

#include <iostream>
#include <string>
#include <memory>
#include <csignal>
#include <stdio.h>
#include <pthread.h>
#include <unordered_map>
#include "xapp_rmr.hpp"
#include "xapp_sdl.hpp"
#include "rapidjson/writer.h"
#include "rapidjson/document.h"
#include "rapidjson/error/error.h"

#include "msgs_proc.hpp"
#include "subs_mgmt.hpp"
#include "xapp_config.hpp"

extern "C" {
  #include "rnib/rnibreader.h"
}

#include "agent_connector.hpp"
#include "e2ap_control_request.hpp"
#include "e2sm_control.hpp"

using namespace std;
using namespace std::placeholders;
using namespace rapidjson;

#define SOCKET_PORT_EXT 7000
#define SOCKET_PORT_EXT_PROTOBUF 7001
#define XAPP_TERMINATE "terminate"
#define TERMINATE_ALL_KEYWORD "all"

// id of gnb to control as seen from the ric
// #define GNB_ID ""

#define DEBUG 0


class Xapp{
public:

    Xapp(XappSettings &, XappRmr &, bool protobuf);

    ~Xapp(void);

    void stop(void);

    void startup(SubscriptionHandler &);
    void shutdown(void);

    void start_xapp_receiver(XappMsgHandler &);
    void Run();

    void sdl_data(void);

    Xapp(Xapp const &)=delete;
    Xapp& operator=(Xapp const &) = delete;

    void register_handler(XappMsgHandler &fn){
        _callbacks.emplace_back(fn);
    }

  //getters/setters.
    void set_rnib_gnblist(void);
    std::vector<std::string> get_rnib_gnblist(){ return rnib_gnblist; }

private:
    void startup_subscribe_requests(void );
    void shutdown_subscribe_deletes(void);
    void startup_get_policies(void );
    void send_ric_control_request(char* payload, int payload_len, std::string gnb_id);

    void handle_rx_msg_agent(std::string agent_ip);
    void handle_external_control_message(int port);
    void terminate_du_reporting_all(void);
    void terminate_du_reporting_single(std::string gnb_id);
    int oneshot_external_control_message_udp(int port, char** buffer);

    XappRmr * rmr_ref;
    XappSettings * config_ref;
    SubscriptionHandler *subhandler_ref;

    std::mutex *xapp_mutex;
    std::vector<std::thread> xapp_rcv_thread;
    std::vector<std::string> rnib_gnblist;
    std::vector<XappMsgHandler> _callbacks;

    std::vector<std::unique_ptr<std::thread>> control_thr_rx;
    std::unique_ptr<std::thread> ext_control_thr_rx;

    char* indreq_buf;
    int indreq_buflen;

    bool using_protobuf;
};


#endif /* SRC_XAPP_HPP_ */
