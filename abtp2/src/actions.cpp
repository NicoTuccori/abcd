/*
 * (C) Copyright 2016 Cristiano Lino Fontana
 *
 * This file is part of ABCD.
 *
 * ABCD is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * ABCD is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with ABCD.  If not, see <http://www.gnu.org/licenses/>.
 */

// This is a personal academic project. Dear PVS-Studio, please check it.
// PVS-Studio Static Code Analyzer for C, C++ and C#: http://www.viva64.com

#include <chrono>
#include <cmath>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>
#include <unistd.h>
#include <zmq.h>
#include <thread>

#include <jansson.h>

extern "C" {
#include "defaults.h"
#include "utilities_functions.h"
#include "socket_functions.h"
#include "jansson_socket_functions.h"
}

#include "typedefs.hpp"
#include "events.hpp"
#include "states.hpp"
#include "actions.hpp"

#define BUFFER_SIZE 32

/******************************************************************************/
/* Generic actions                                                            */
/******************************************************************************/

void actions::generic::publish_events(status &global_status)
{
    const size_t waveforms_buffer_size = global_status.waveforms_buffer.size();

    if (waveforms_buffer_size > 0)
    {
        size_t total_size = 0;

        for (auto &event: global_status.waveforms_buffer)
        {
            total_size += event.size();
        }

        std::vector<uint8_t> output_buffer(total_size);

        size_t portion = 0;

        for (auto &event: global_status.waveforms_buffer)
        {
            const size_t event_size = event.size();
            const std::vector<uint8_t> event_buffer = event.serialize();

            memcpy(output_buffer.data() + portion,
                   reinterpret_cast<const void*>(event_buffer.data()),
                   event_size);

            portion += event_size;
        }

        std::string topic = defaults_abcd_data_waveforms_topic;
        topic += "_v0_s";
        topic += std::to_string(total_size);

        if (global_status.verbosity > 0)
        {
            char time_buffer[BUFFER_SIZE];
            time_string(time_buffer, BUFFER_SIZE, NULL);
            std::cout << '[' << time_buffer << "] ";
            std::cout << "Sending waveforms buffer; ";
            std::cout << "Topic: " << topic << "; ";
            std::cout << "waveforms: " << waveforms_buffer_size << "; ";
            std::cout << "buffer size: " << total_size << "; ";
            std::cout << std::endl;
        }

        const bool result = send_byte_message(global_status.data_socket,
                                              topic.c_str(),
                                              output_buffer.data(),
                                              total_size,
                                              1);

        if (result == EXIT_FAILURE)
        {
            char time_buffer[BUFFER_SIZE];
            time_string(time_buffer, BUFFER_SIZE, NULL);
            std::cout << '[' << time_buffer << "] ";
            std::cout << "ERROR: ZeroMQ Error publishing events";
            std::cout << std::endl;
        }

        // Cleanup vector
        global_status.waveforms_buffer.clear();
        // Initialize vector size to its max size plus a 10%
        global_status.waveforms_buffer.reserve(global_status.events_buffer_max_size
                                               + global_status.events_buffer_max_size / 10);
    }
}

void actions::generic::publish_message(status &global_status,
                                       std::string topic,
                                       json_t *status_message)
{
    std::chrono::time_point<std::chrono::system_clock> last_publication = std::chrono::system_clock::now();
    global_status.last_publication = last_publication;

    void *status_socket = global_status.status_socket;
    const unsigned long int status_msg_ID = global_status.status_msg_ID;

    char time_buffer[BUFFER_SIZE];
    time_string(time_buffer, BUFFER_SIZE, NULL);

    json_object_set_new(status_message, "module", json_string("abcd"));
    json_object_set_new(status_message, "timestamp", json_string(time_buffer));
    json_object_set_new(status_message, "msg_ID", json_integer(status_msg_ID));

    char *output_buffer = json_dumps(status_message, JSON_COMPACT);

    if (!output_buffer)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: Unable to allocate status output buffer; ";
        std::cout << std::endl;
    }
    else
    {
        size_t total_size = strlen(output_buffer);

        topic += "_v0_s";
        topic += std::to_string(total_size);

        if (global_status.verbosity > 0)
        {
            char time_buffer[BUFFER_SIZE];
            time_string(time_buffer, BUFFER_SIZE, NULL);
            std::cout << '[' << time_buffer << "] ";
            std::cout << "Sending status message; ";
            std::cout << "Topic: " << topic << "; ";
            std::cout << "buffer size: " << total_size << "; ";
            std::cout << "message: " << output_buffer << "; ";
            std::cout << std::endl;
        }

        send_byte_message(status_socket, topic.c_str(), output_buffer, total_size, 1);

        free(output_buffer);
    }

    global_status.status_msg_ID += 1;
}

void actions::generic::stop_acquisition(status &global_status)
{
    const unsigned int verbosity = global_status.verbosity;

    if (verbosity > 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "#### Stopping acquisition!!! ";
        std::cout << std::endl;
    }

    // Stop acquisition
    // TO DO

    std::chrono::time_point<std::chrono::system_clock> stop_time = std::chrono::system_clock::now();
    auto delta_time = std::chrono::duration_cast<std::chrono::duration<long int>>(stop_time - global_status.start_time);

    global_status.stop_time = stop_time;

    if (verbosity > 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "Run time: ";
        std::cout << delta_time.count();
        std::cout << std::endl;
    }
}

void actions::generic::clear_memory(status &global_status)
{
    
    // TO DO
    
}

void actions::generic::destroy_digitizer(status &global_status)
{
	
    if (global_status.verbosity > 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "Destroying digitizer ";
        std::cout << std::endl;
    }

    // TO DO
    
}


bool actions::generic::create_digitizer(status &global_status) {

    unsigned int verbosity = global_status.verbosity;

    /// Remove socket file if it exists
    struct stat buffer;
    if (stat(global_status.clientSocketName, &buffer) == 0) {
        std::cout << "Found existing " << global_status.clientSocketName << ". Removing." << std::endl;
        if (unlink(global_status.clientSocketName) != 0) {
            std::cerr << "Failed to remove " << global_status.clientSocketName << ": "
                      << strerror(errno) << std::endl;
        }
    }

    // Remove shared memory if it exists
    if (stat(global_status.shmName, &buffer) == 0) {
        std::cout << "Found existing " << global_status.shmName << ". Removing." << std::endl;
        if (unlink(global_status.shmName) != 0) {
            std::cerr << "Failed to remove " << global_status.shmName << ": "
                      << strerror(errno) << std::endl;
        }
    }
    // std::system("pkill daqd");    

    // Start daqd
    if (verbosity > 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "Opening petsys device; ";
        std::cout << std::endl;
    }
    global_status.clientSocket = createListeningSocket(global_status.clientSocketName);

    if(global_status.clientSocket < 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: Unable to open device";
        std::cout << std::endl;
        
        if(global_status.clientSocket != -1) {
            close(global_status.clientSocket);
            unlink(global_status.clientSocketName);
        }
            
        return false;
	}


    if (verbosity > 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "Connected to PETsys daqd successfully to socket" << global_status.clientSocketName << ".";
        std::cout << std::endl;
    }

    if (verbosity > 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "Allocate Shared memory";
        std::cout << std::endl;
    }

    PETSYS::FrameServer::allocateSharedMemory(global_status.shmName, global_status.shmfd, global_status.shmPtr);
	if((global_status.shmfd == -1) || (global_status.shmPtr == NULL)) {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: freeing allocated memory";
        std::cout << std::endl;
		PETSYS::FrameServer::freeSharedMemory(global_status.shmName, global_status.shmfd, global_status.shmPtr);
        return false;
	}

    if (verbosity > 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "Create frame server";
        std::cout << std::endl;
    }

    if (global_status.daqType == 0) {
		global_status.frameServer = PETSYS::UDPFrameServer::createFrameServer(  global_status.shmName, 
                                                                                global_status.shmfd, 
                                                                                global_status.shmPtr, 
                                                                                global_status.verbosity);
	}
	else if (global_status.daqType == 1) {
		for(auto i = global_status.daqCardList.begin(); i != global_status.daqCardList.end(); i++) {
			PETSYS::AbstractDAQCard *card = PETSYS::PFP_KX7::openCard(i->c_str());
			if(card == NULL) {
                for(auto iter = global_status.daqCards.begin(); iter != global_status.daqCards.end(); iter++) {
                    delete *iter;
                }
            }
			global_status.daqCards.push_back(card);
		}
        global_status.frameServer = PETSYS::DAQFrameServer::createFrameServer(  global_status.daqCards, 
                                                                                global_status.daqCardPortBits,
                                                                                global_status.shmName, 
                                                                                global_status.shmfd, 
                                                                                global_status.shmPtr, 
                                                                                global_status.verbosity);
	}
	
	if(global_status.frameServer == NULL) {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: allocating frame server";
        std::cout << std::endl;
		if(global_status.frameServer != NULL) delete global_status.frameServer;
        return false;
	}

    std::thread socketThread(pollSocket, global_status.clientSocket, global_status.frameServer);
    socketThread.detach();  // Run in background, detached
    // pollSocket(global_status.clientSocket, global_status.frameServer);

    return true;
}


bool actions::generic::configure_digitizer(status &global_status)
{
    unsigned int verbosity = global_status.verbosity;

    json_t *config = global_status.config;
    json_t *value;

    // TO DO
     
    return true;
}

bool actions::generic::allocate_memory(status &global_status)
{
    unsigned int verbosity = global_status.verbosity;
      
    return true;

}

/******************************************************************************/
/* Specific actions                                                           */
/******************************************************************************/

state actions::start(status&)
{
    return states::CREATE_CONTEXT;
}

state actions::create_context(status &global_status)
{
    // Creates a ØMQ context
    void *context = zmq_ctx_new();
    if (!context)
    {
        // No errors are defined for this function
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: ZeroMQ Error on context creation";
        std::cout << std::endl;

        return states::COMMUNICATION_ERROR;
    }

    global_status.context = context;

    std::this_thread::sleep_for(std::chrono::milliseconds(defaults_abcd_zmq_delay));

    return states::CREATE_SOCKETS;
}

state actions::create_sockets(status &global_status)
{
    void *context = global_status.context;

    // Creates the status socket
    void *status_socket = zmq_socket(context, ZMQ_PUB);
    if (!status_socket)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: ZeroMQ Error on status socket creation: ";
        std::cout << zmq_strerror(errno);
        std::cout << std::endl;

        return states::COMMUNICATION_ERROR;
    }

    // Creates the data socket
    void *data_socket = zmq_socket(context, ZMQ_PUB);
    if (!data_socket)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: ZeroMQ Error on data socket creation: ";
        std::cout << zmq_strerror(errno);
        std::cout << std::endl;

        return states::COMMUNICATION_ERROR;
    }

    // Creates the commands socket
    void *commands_socket = zmq_socket(context, ZMQ_PULL);
    if (!commands_socket)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: ZeroMQ Error on commands socket creation: ";
        std::cout << zmq_strerror(errno);
        std::cout << std::endl;

        return states::COMMUNICATION_ERROR;
    }

    global_status.status_socket = status_socket;
    global_status.data_socket = data_socket;
    global_status.commands_socket = commands_socket;

    std::this_thread::sleep_for(std::chrono::milliseconds(defaults_abcd_zmq_delay));

    return states::BIND_SOCKETS;
}

state actions::bind_sockets(status &global_status)
{
    std::string status_address = global_status.status_address;
    std::string data_address = global_status.data_address;
    std::string commands_address = global_status.commands_address;

    // Binds the status socket to its address
    const int s = zmq_bind(global_status.status_socket, status_address.c_str());
    if (s != 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: ZeroMQ Error on status socket binding: ";
        std::cout << zmq_strerror(errno);
        std::cout << std::endl;

        return states::COMMUNICATION_ERROR;
    }

    // Binds the data socket to its address
    const int d = zmq_bind(global_status.data_socket, data_address.c_str());
    if (d != 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: ZeroMQ Error on data socket binding: ";
        std::cout << zmq_strerror(errno);
        std::cout << std::endl;

        return states::COMMUNICATION_ERROR;
    }

    // Binds the socket to its address
    const int c = zmq_bind(global_status.commands_socket, commands_address.c_str());
    if (c != 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: ZeroMQ Error on commands socket binding: ";
        std::cout << zmq_strerror(errno);
        std::cout << std::endl;

        return states::COMMUNICATION_ERROR;
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(defaults_abcd_zmq_delay));

    return states::READ_CONFIG;
}

state actions::read_config(status &global_status)
{
    const std::string config_file_name = global_status.config_file;

    if (global_status.verbosity > 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "Reading config file: " << config_file_name << " ";
        std::cout << std::endl;
    }

    json_error_t error;

    json_t *new_config = json_load_file(config_file_name.c_str(), 0, &error);

    if (!new_config)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: Parse error while reading config file: ";
        std::cout << error.text;
        std::cout << " (source: ";
        std::cout << error.source;
        std::cout << ", line: ";
        std::cout << error.line;
        std::cout << ", column: ";
        std::cout << error.column;
        std::cout << ", position: ";
        std::cout << error.position;
        std::cout << "); ";
        std::cout << std::endl;

        return states::PARSE_ERROR;
    }
    else
    {
        global_status.config = new_config;

        return states::CREATE_DIGITIZER;
    }
}

state actions::create_digitizer(status &global_status)
{
    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("event"));
    json_object_set_new_nocheck(json_event_message, "event", json_string("Digitizer initialization"));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    const bool success = actions::generic::create_digitizer(global_status);

    if (success)
    {
        return states::CONFIGURE_DIGITIZER;
    }
    else
    {
        return states::CONFIGURE_ERROR;
    }
}

state actions::recreate_digitizer(status &global_status)
{
    const bool success = actions::generic::create_digitizer(global_status);

    if (success)
    {
        return states::CONFIGURE_DIGITIZER;
    }
    else
    {
        return states::CONFIGURE_ERROR;
    }
}

state actions::configure_digitizer(status &global_status)
{
    const bool success = actions::generic::configure_digitizer(global_status);

    if (success)
    {
        return states::ALLOCATE_MEMORY;
    }
    else
    {
        return states::CONFIGURE_ERROR;
    }
}

state actions::reconfigure_destroy_digitizer(status &global_status)
{
    actions::generic::destroy_digitizer(global_status);

    return states::RECREATE_DIGITIZER;
}

state actions::receive_commands(status &global_status)
{
    void *commands_socket = global_status.commands_socket;

    char *buffer;
    size_t size;
    
    const int result = receive_byte_message(commands_socket, nullptr, (void**)(&buffer), &size, 0, global_status.verbosity);

    if (global_status.verbosity > 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "result: " << result << "; ";
        std::cout << "size: " << size << "; ";
        std::cout << std::endl;
    }

    if (size > 0 && result == EXIT_SUCCESS)
    {
        if (global_status.verbosity > 0)
        {
            char time_buffer[BUFFER_SIZE];
            time_string(time_buffer, BUFFER_SIZE, NULL);
            std::cout << '[' << time_buffer << "] ";
            std::cout << "Message buffer: ";
            std::cout << (char*)buffer;
            std::cout << "; ";
            std::cout << std::endl;
        }

        std::string error_string;

        json_error_t error;
        json_t *json_message = json_loadb(buffer, size, 0, &error);

        free(buffer);

        if (!json_message)
        {
            char time_buffer[BUFFER_SIZE];
            time_string(time_buffer, BUFFER_SIZE, NULL);
            std::cout << '[' << time_buffer << "] ";
            std::cout << "ERROR: ";
            std::cout << error.text;
            std::cout << " (source: ";
            std::cout << error.source;
            std::cout << ", line: ";
            std::cout << error.line;
            std::cout << ", column: ";
            std::cout << error.column;
            std::cout << ", position: ";
            std::cout << error.position;
            std::cout << "); ";
            std::cout << std::endl;
        }
        else
        {
            const size_t command_ID = json_integer_value(json_object_get(json_message, "msg_ID"));
            const std::string command = json_string_value(json_object_get(json_message, "command"));
            json_t *json_arguments = json_object_get(json_message, "arguments");

            if (global_status.verbosity > 0)
            {
                char time_buffer[BUFFER_SIZE];
                time_string(time_buffer, BUFFER_SIZE, NULL);
                std::cout << '[' << time_buffer << "] ";
                std::cout << "Command ID: " << command_ID << "; ";
                std::cout << std::endl;
            }

            if (command == std::string("start"))
            {
                char time_buffer[BUFFER_SIZE];
                time_string(time_buffer, BUFFER_SIZE, NULL);
                std::cout << '[' << time_buffer << "] ";
                std::cout << "################################################################### Start!!! ###";
                std::cout << std::endl;

                return states::START_ACQUISITION;
            }
            else if (command == std::string("reconfigure") && json_arguments)
            {
                json_t *new_config = json_object_get(json_arguments, "config");

                // Remember to clean up
                json_decref(global_status.config);

                // This is a borrowed reference, so we shall increment the reference count
                global_status.config = new_config;
                json_incref(global_status.config);

                json_t *json_event_message = json_object();

                json_object_set_new_nocheck(json_event_message, "type", json_string("event"));
                json_object_set_new_nocheck(json_event_message, "event", json_string("Digitizer reconfiguration"));

                actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

                json_decref(json_event_message);
										
                return states::CONFIGURE_DIGITIZER;
            }
            else if (command == std::string("off"))
            {
                return states::CLEAR_MEMORY;
            }
            else if (command == std::string("quit"))
            {
                return states::CLEAR_MEMORY;
            }

            json_decref(json_message);
        }
    }

    const std::chrono::time_point<std::chrono::system_clock> now = std::chrono::system_clock::now();
    if (now - global_status.last_publication > std::chrono::seconds(defaults_abcd_publish_timeout))
    {
        return states::PUBLISH_STATUS;
    }

    return states::RECEIVE_COMMANDS;
}

state actions::publish_status(status &global_status)
{
    // TO DO

    json_t *status_message = json_object();

    json_object_set_new_nocheck(status_message, "config", json_deep_copy(global_status.config));

    json_t *acquisition = json_object();
    json_object_set_new_nocheck(acquisition, "running", json_false());
    json_object_set_new_nocheck(status_message, "acquisition", acquisition);

    json_t *digitizer = json_object();

    if (false)
    {
        json_object_set_new_nocheck(digitizer, "valid_pointer", json_false());
        json_object_set_new_nocheck(digitizer, "active", json_false());
    }
    else
    {
        json_object_set_new_nocheck(digitizer, "valid_pointer", json_true());
        json_object_set_new_nocheck(digitizer, "active", json_true());
    }

    json_object_set_new_nocheck(status_message, "digitizer", digitizer);

    actions::generic::publish_message(global_status, defaults_abcd_status_topic, status_message);

    json_decref(status_message);

    // TO DO
    if (true)
    {
        return states::RECEIVE_COMMANDS;
    }
    else
    {
        return states::DIGITIZER_ERROR;
    }
}

state actions::allocate_memory(status &global_status)
{
    const bool success = actions::generic::allocate_memory(global_status);

    if (success)
    {
        return states::PUBLISH_STATUS;
    }
    else
    {
        // return states::DIGITIZER_ERROR;
        return states::DESTROY_DIGITIZER;
    }
}

state actions::restart_allocate_memory(status &global_status)
{
    const bool success = actions::generic::allocate_memory(global_status);

    if (success)
    {
        return states::START_ACQUISITION;
    }
    else
    {
        return states::RESTART_CONFIGURE_ERROR;
    }
}

state actions::stop(status&)
{
    return states::STOP;
}

state actions::start_acquisition(status &global_status)
{
    // TO DO
   
    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("event"));
    json_object_set_new_nocheck(json_event_message, "event", json_string("Start acquisition"));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    // TO DO

    // Start acquisition 
    std::chrono::time_point<std::chrono::system_clock> start_time = std::chrono::system_clock::now();
    
    // TO DO

    global_status.start_time = start_time;
    global_status.block_start_time = start_time;

    return states::ACQUISITION_RECEIVE_COMMANDS;
}

state actions::acquisition_receive_commands(status &global_status)
{
    void *commands_socket = global_status.commands_socket;

    char *buffer;
    size_t size;
    
    const int result = receive_byte_message(commands_socket, nullptr, (void**)(&buffer), &size, 0, global_status.verbosity);

    if (global_status.verbosity > 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "result: " << result << "; ";
        std::cout << "size: " << size << "; ";
        std::cout << std::endl;
    }

    if (size > 0 && result == EXIT_SUCCESS)
    {
        if (global_status.verbosity > 0)
        {
            char time_buffer[BUFFER_SIZE];
            time_string(time_buffer, BUFFER_SIZE, NULL);
            std::cout << '[' << time_buffer << "] ";
            std::cout << "Message buffer: ";
            std::cout << (char*)buffer;
            std::cout << "; ";
            std::cout << std::endl;
        }

        std::string error_string;

        json_error_t error;
        json_t *json_message = json_loadb(buffer, size, 0, &error);

        free(buffer);

        if (!json_message)
        {
            char time_buffer[BUFFER_SIZE];
            time_string(time_buffer, BUFFER_SIZE, NULL);
            std::cout << '[' << time_buffer << "] ";
            std::cout << "ERROR: ";
            std::cout << error.text;
            std::cout << " (source: ";
            std::cout << error.source;
            std::cout << ", line: ";
            std::cout << error.line;
            std::cout << ", column: ";
            std::cout << error.column;
            std::cout << ", position: ";
            std::cout << error.position;
            std::cout << "); ";
            std::cout << std::endl;
        }
        else
        {
            const size_t command_ID = json_integer_value(json_object_get(json_message, "msg_ID"));
            const std::string command = json_string_value(json_object_get(json_message, "command"));

            if (global_status.verbosity > 0)
            {
                char time_buffer[BUFFER_SIZE];
                time_string(time_buffer, BUFFER_SIZE, NULL);
                std::cout << '[' << time_buffer << "] ";
                std::cout << "Command ID: " << command_ID << "; ";
                std::cout << std::endl;
            }

            if (command == std::string("stop"))
            {
                char time_buffer[BUFFER_SIZE];
                time_string(time_buffer, BUFFER_SIZE, NULL);
                std::cout << '[' << time_buffer << "] ";
                std::cout << "#################################################################### Stop!!! ###";
                std::cout << std::endl;

                return states::STOP_PUBLISH_EVENTS;
            }

            json_decref(json_message);
        }
    }

    return states::ADD_TO_BUFFER;
}

state actions::add_to_buffer(status &global_status)
{
    const unsigned int verbosity = global_status.verbosity;

    const std::chrono::time_point<std::chrono::system_clock> now = std::chrono::system_clock::now();

    int16_t poll_success;

    // TO DO
    
    return states::ADD_TO_BUFFER;
}

state actions::publish_events(status &global_status)
{
    actions::generic::publish_events(global_status);

    return states::ACQUISITION_PUBLISH_STATUS;
    
}

state actions::stop_publish_events(status &global_status)
{
    actions::generic::publish_events(global_status);

    return states::STOP_ACQUISITION;
}

state actions::acquisition_publish_status(status &global_status)
{
    // TO DO

    json_t *status_message = json_object();

    json_object_set_new_nocheck(status_message, "config", json_deep_copy(global_status.config));

    json_t *acquisition = json_object();
    json_t *digitizer = json_object();

    // TO DO
    
    if (true) 
    {   
        return states::ACQUISITION_RECEIVE_COMMANDS; //If no events, nothing have been published and the acquisition is still running
    }
    else 
    {
        // TO DO

        return states::CONTINUE_ACQUISITION; //START ANOTHER RUN BLOCK
    }
}

state actions::continue_acquisition(status &global_status)
{
    // TO DO

    return states::ACQUISITION_RECEIVE_COMMANDS;
}

state actions::trigger_reconfiguration(status &global_status)
{
    // TO DO
															 
    return states::PUBLISH_EVENTS;
}

state actions::stop_acquisition(status &global_status)
{
    actions::generic::stop_acquisition(global_status);

    auto delta_time = std::chrono::duration_cast<std::chrono::duration<long int>>(global_status.stop_time - global_status.start_time);
    const std::string event_message = "Stop acquisition (duration: " + std::to_string(delta_time.count()) + " s)";

    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("event"));
    json_object_set_new_nocheck(json_event_message, "event", json_string(event_message.c_str()));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    return states::RECEIVE_COMMANDS;
}

state actions::clear_memory(status &global_status)
{
    // TO DO
        
    if(true)
    {
        actions::generic::clear_memory(global_status);
    }
    else
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: petsys is not ok right now!";
        std::cout << std::endl;
    }

    return states::DESTROY_DIGITIZER;
}

state actions::reconfigure_clear_memory(status &global_status)
{
    // TO DO
        
    if(true)
    {
        actions::generic::clear_memory(global_status);
    }
    else
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ERROR: petsys is not ok right now!";
        std::cout << std::endl;
    
        return states::CONFIGURE_ERROR;
    }

    return states::RECONFIGURE_DESTROY_DIGITIZER;
}

state actions::destroy_digitizer(status &global_status)
{
    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("event"));
    json_object_set_new_nocheck(json_event_message, "event", json_string("Digitizer deactivation"));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    actions::generic::destroy_digitizer(global_status);

    return states::CLOSE_SOCKETS;
}

state actions::restart_publish_events(status &global_status)
{
    actions::generic::publish_events(global_status);

    return states::RESTART_STOP_ACQUISITION;
}

state actions::restart_stop_acquisition(status &global_status)
{
    actions::generic::stop_acquisition(global_status);

    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("event"));
    json_object_set_new_nocheck(json_event_message, "event", json_string("Restart stop acquisition"));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    return states::RESTART_CLEAR_MEMORY;
}

state actions::restart_clear_memory(status &global_status)
{
    actions::generic::clear_memory(global_status);
    
    return states::RESTART_DESTROY_DIGITIZER;
}

state actions::restart_destroy_digitizer(status &global_status)
{
    actions::generic::destroy_digitizer(global_status);

    return states::RESTART_CREATE_DIGITIZER;
}

state actions::restart_create_digitizer(status &global_status)
{
    const bool success = actions::generic::create_digitizer(global_status);

    if (success)
    {
        return states::RESTART_CONFIGURE_DIGITIZER;
    }
    else
    {
        return states::RESTART_CONFIGURE_ERROR;
    }
}

state actions::restart_configure_digitizer(status &global_status)
{
    const bool success = actions::generic::configure_digitizer(global_status);

    if (success)
    {
        return states::RESTART_ALLOCATE_MEMORY;
    }
    else
    {
        return states::RESTART_CONFIGURE_ERROR;
    }
}

state actions::close_sockets(status &global_status)
{
    std::this_thread::sleep_for(std::chrono::milliseconds(defaults_abcd_zmq_delay));

    void *status_socket = global_status.status_socket;
    void *data_socket = global_status.data_socket;
    void *commands_socket = global_status.commands_socket;

    const int s = zmq_close(status_socket);
    if (s != 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ZeroMQ Error on status socket close: ";
        std::cout << zmq_strerror(errno);
        std::cout << std::endl;
    }

    const int d = zmq_close(data_socket);
    if (d != 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ZeroMQ Error on data socket close: ";
        std::cout << zmq_strerror(errno);
        std::cout << std::endl;
    }

    const int c = zmq_close(commands_socket);
    if (c != 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ZeroMQ Error on commands socket close: ";
        std::cout << zmq_strerror(errno);
        std::cout << std::endl;
    }

    return states::DESTROY_CONTEXT;
}

state actions::destroy_context(status &global_status)
{
    std::this_thread::sleep_for(std::chrono::milliseconds(defaults_abcd_zmq_delay));

    void *context = global_status.context;

    const int c = zmq_ctx_destroy(context);
    if (c != 0)
    {
        char time_buffer[BUFFER_SIZE];
        time_string(time_buffer, BUFFER_SIZE, NULL);
        std::cout << '[' << time_buffer << "] ";
        std::cout << "ZeroMQ Error on context destroy: ";
        std::cout << zmq_strerror(errno);
        std::cout << std::endl;
    }

    return states::STOP;
}

state actions::communication_error(status &global_status)
{
    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("error"));
    json_object_set_new_nocheck(json_event_message, "error", json_string("Communication error"));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    return states::CLOSE_SOCKETS;
}

state actions::parse_error(status &global_status)
{
    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("error"));
    json_object_set_new_nocheck(json_event_message, "error", json_string("Config parse error"));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    return states::CLOSE_SOCKETS;
}

state actions::configure_error(status &global_status)
{
    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("error"));
    json_object_set_new_nocheck(json_event_message, "error", json_string("Configure error"));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    return states::RECONFIGURE_DESTROY_DIGITIZER;
}

state actions::digitizer_error(status &global_status)
{
    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("error"));
    json_object_set_new_nocheck(json_event_message, "error", json_string("Digitizer error"));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    return states::RECONFIGURE_CLEAR_MEMORY;
}

state actions::acquisition_error(status &global_status)
{
    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("error"));
    json_object_set_new_nocheck(json_event_message, "error", json_string("Acquisition error"));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    return states::RESTART_PUBLISH_EVENTS;
}

state actions::restart_configure_error(status &global_status)
{
    json_t *json_event_message = json_object();

    json_object_set_new_nocheck(json_event_message, "type", json_string("error"));
    json_object_set_new_nocheck(json_event_message, "error", json_string("Restart configure error"));

    actions::generic::publish_message(global_status, defaults_abcd_events_topic, json_event_message);

    json_decref(json_event_message);

    return states::RESTART_DESTROY_DIGITIZER;
}
