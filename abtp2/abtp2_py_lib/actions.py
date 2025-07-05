import zmq, json, time
from datetime import datetime
import logging
from .library import send_byte_message, receive_byte_message
from .typedefs import status
from . import states

import sys
import os

from .petsys_lib import daqd

# Define or import your delay constant (ms)
defaults_abcd_zmq_delay = 100  # replace with actual constant if needed

# Helper debug printer
def dbg(s, *args):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] " + s.format(*args))

def start(s: status):
    logging.info(f"Start\t\t\t-> GO\t-> CREATE CONTEXT")
    return states.CREATE_CONTEXT

def stop(s: status):
    return states.STOP

def create_context(s: status):
    try:
        context = zmq.Context()
    except Exception as e:
        logging.error(f"ZeroMQ Error on context creation: {e}")
        return states.COMMUNICATION_ERROR

    s.context = context

    time.sleep(defaults_abcd_zmq_delay / 1000.0)  # delay in seconds
    logging.info(f"Create context\t\t-> OK\t-> CREATE SOCKETS")

    return states.CREATE_SOCKETS

def create_sockets(s: status):
    context = s.context

    try:
        # Create the status PUB socket
        status_socket = context.socket(zmq.PUB)
    except Exception as e:
        logging.error(f"ZeroMQ Error on status socket creation: {e}")
        return states.COMMUNICATION_ERROR

    try:
        # Create the data PUB socket
        data_socket = context.socket(zmq.PUB)
    except Exception as e:
        logging.error(f"ZeroMQ Error on data socket creation: {e}")
        return states.COMMUNICATION_ERROR

    try:
        # Create the commands PULL socket
        commands_socket = context.socket(zmq.PULL)
    except Exception as e:
        logging.error(f"ZeroMQ Error on commands socket creation: {e}")
        return states.COMMUNICATION_ERROR

    # Assign sockets to status object
    s.status_socket = status_socket
    s.data_socket = data_socket
    s.commands_socket = commands_socket

    time.sleep(defaults_abcd_zmq_delay / 1000.0)  # sleep uses seconds
    logging.info(f"Sockets create\t\t-> OK\t-> BIND SOCKETS")

    return states.BIND_SOCKETS

def bind_sockets(s: status):
    try:
        s.status_socket.bind(s.status_address)
    except zmq.ZMQError as e:
        logging.error(f"ZeroMQ Error on status socket binding: {e}")
        return states.COMMUNICATION_ERROR

    try:
        s.data_socket.bind(s.data_address)
    except zmq.ZMQError as e:
        logging.error(f"ZeroMQ Error on data socket binding: {e}")
        return states.COMMUNICATION_ERROR

    try:
        s.commands_socket.bind(s.commands_address)
    except zmq.ZMQError as e:
        logging.error(f"ZeroMQ Error on commands socket binding: {e}")
        return states.COMMUNICATION_ERROR

    time.sleep(defaults_abcd_zmq_delay / 1000.0)  # sleep in seconds
    logging.info(f"Bind sockets\t\t-> OK\t-> READ CONFIG")

    return states.READ_CONFIG

def read_config(s: status):
    config_file_name = s.config_file

    if s.verbosity > 0:
        time_str = datetime.now().isoformat()
        print(f"[{time_str}] Reading config file: {config_file_name}")

    try:
        with open(config_file_name, 'r') as f:
            new_config = json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Parse error while reading config file: {e.msg} "
              f"(line: {e.lineno}, column: {e.colno})")
        return states.PARSE_ERROR
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_file_name}")
        return states.PARSE_ERROR
    except Exception as e:
        logging.error(f"Unexpected error reading config file: {e}")
        return states.PARSE_ERROR

    s.config = new_config
    logging.info(f"Read config\t\t-> OK\t-> CREATE DIGITIZER")
    # return states.CREATE_DIGITIZER
    return states.COMMUNICATION_ERROR

def parse_error(s: status):
    # Construct the error message as a Python dict (equivalent to JSON object)
    json_event_message = {
        "type": "error",
        "error": "Communication error"
    }

    # Publish the error message on the events topic
    # generic_actions.publish_message(s, "events_topic", json_event_message)  # replace "events_topic" with your actual topic constant

    # No explicit JSON ref decrement needed in Python (GC handles it)

    logging.info(f"Parse error\t\t-> OK\t-> CLOSE SOCKETS")

    return states.CLOSE_SOCKETS

def communication_error(s: status):
    # Construct the error message as a Python dict (equivalent to JSON object)
    json_event_message = {
        "type": "error",
        "error": "Communication error"
    }

    # Publish the error message on the events topic
    # generic_actions.publish_message(s, "events_topic", json_event_message)  # replace "events_topic" with your actual topic constant

    # No explicit JSON ref decrement needed in Python (GC handles it)

    logging.info(f"Communication error\t-> OK\t-> CLOSE SOCKETS")

    return states.CLOSE_SOCKETS

def close_sockets(s: status):
    time.sleep(defaults_abcd_zmq_delay / 1000.0)  # delay in seconds

    def try_close_socket(socket, name):
        try:
            socket.close()
        except zmq.ZMQError as e:
            logging.error(f"ZeroMQ Error on {name} socket close: {e}")

    try_close_socket(s.status_socket, "status")
    try_close_socket(s.data_socket, "data")
    try_close_socket(s.commands_socket, "commands")

    logging.info(f"Close sockets\t\t-> OK\t-> DESTROY CONTEXT")

    return states.DESTROY_CONTEXT

def destroy_context(s: status):
    time.sleep(defaults_abcd_zmq_delay / 1000.0)  # delay in seconds

    context = s.context
    if context is not None:
        try:
            context.term()  # equivalent to zmq_ctx_destroy
        except zmq.ZMQError as e:
            logging.error(f"ZeroMQ Error on context destroy: {e}")

    logging.info(f"Destroy context\t\t-> OK\t-> STOP")

    return states.STOP