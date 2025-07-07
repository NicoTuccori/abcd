# -----------------------------------------------------------------------------
# This file is part of ABCD.
# 2025 Nicolò Tuccori
# -----------------------------------------------------------------------------

"""
Actions to interface and read PETsys TOFPET2 ASICs
Python-version of standard ABCD actions
"""

import zmq, json, time
from datetime import datetime
import logging
from .library import send_byte_message, receive_byte_message
from .typedefs import status, daqd_daemon
from . import states

import os

from .petsys_lib import daqd, config

# Define or import your delay constant (ms)
defaults_abcd_zmq_delay = 100  # replace with actual constant if needed
defaults_abcd_events_topic = "events_abcd"

#******************************************************************************/
#* Generic actions                                                            */
#******************************************************************************/

def generic_publish_message(s: status, topic: str, status_message: dict):
    # Update timestamp and message ID
    s.last_publication = datetime.now()
    status_message["module"] = "abtp2"
    status_message["timestamp"] = s.last_publication.isoformat()
    status_message["msg_ID"] = s.status_msg_ID

    try:
        output_buffer = json.dumps(status_message, separators=(",", ":")).encode('utf-8')
    except (TypeError, ValueError) as e:
        logging.error(f"Unable to encode status message to JSON: {e}")
        return

    total_size = len(output_buffer)
    topic_with_suffix = f"{topic}_v0_s{total_size}".encode('utf-8')

    if s.verbosity > 0:
        logging.info(f"Sending status message; Topic: {topic_with_suffix.decode()}; "
                     f"Size: {total_size}; Message: {output_buffer.decode(errors='replace')}")

    success = send_byte_message(
        socket=s.status_socket,
        topic=topic_with_suffix,
        buffer=output_buffer,
        verbosity=s.verbosity
    )

    if not success:
        logging.warning("Message failed to send on ZeroMQ socket.")

    s.status_msg_ID += 1

def generic_create_digitizer(s: status) -> bool:

    # Remove socket file if it exists
    if os.path.exists(s.client_socket_name):
        if s.verbosity > 0:
            logging.info(f"Found existing {s.client_socket_name}, removing.")
        try:
            os.unlink(s.client_socket_name)
        except Exception as e:
            logging.error(f"Failed to remove {s.client_socket_name}: {e}")
            return False

    # Remove shared memory file if it exists
    if os.path.exists(s.shm_name):
        if s.verbosity > 0:
            logging.info(f"Found existing {s.shm_name}, removing.")
        try:
            os.unlink(s.shm_name)
        except Exception as e:
            logging.error(f"Failed to remove {s.shm_name}: {e}")
            return False

    # Start daqd
    if s.verbosity > 0:
        logging.info("Starting C++ DAQ daemon")
    
    # Initialize and start the C++ daqd daemon
    try:
        s.daemon = daqd_daemon(
            daqd_executable='./abtp2_py_lib/petsys_lib/daqd',
            daq_type=s.daq_type,
            socket_path=s.client_socket_name,
            debug_level=2,
            card_paths=s.daq_cards
        )
        logging.info("DAQ daemon started successfully.")
    except Exception as e:
        logging.error(f"Failed to start DAQ daemon: {e}")
        return False

    s.connection = daqd.Connection()
    # s.connection.initializeSystem()

    return True

def generic_destroy_digitizer(s: status) -> None:

    if s.verbosity > 0:
        logging.info("Destroying digitizer")
        logging.info("Shutting down DAQ daemon")
    try:
        s.daemon.stop()
    except Exception as e:
        logging.error(f"Error during shutdown: {e}")

    # TO DO

#******************************************************************************/
#* Digitizer-specific actions                                                   */
#******************************************************************************/

def read_config(s: status):
    config_file_name = s.config_file

    if s.verbosity > 0:
        logging.info(f"Reading config file: {config_file_name}")

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
    if s.verbosity > 0:
        logging.info(f"Read config\t\t-> OK\t-> CREATE DIGITIZER")
    return states.CREATE_DIGITIZER
    # return states.COMMUNICATION_ERROR

def create_digitizer(s: status):
    
    json_event_message = {
        "type": "event",
        "event": "Digitizer initialization"
    }

    generic_publish_message(s, defaults_abcd_events_topic, json_event_message)

    # Call the digitizer creation logic
    success = generic_create_digitizer(s)

    if success:
        if s.verbosity > 0:
            logging.info("Create digitizer\t\t-> OK\t-> CONFIGURE_DIGITIZER")
        time.sleep(20)
        # return states.CONFIGURE_DIGITIZER
        return states.DESTROY_DIGITIZER
    else:
        logging.error("Digitizer creation failed")
        return states.CONFIGURE_ERROR
    
def destroy_digitizer(s: status):

    json_event_message = {
        "type": "event",
        "event": "Digitizer deactivation"
    }

    generic_publish_message(s, defaults_abcd_events_topic, json_event_message)

    generic_destroy_digitizer(s)

    return states.CLOSE_SOCKETS

#******************************************************************************/
#* Sockets-specific actions                                                   */
#******************************************************************************/

def start(s: status):
    if s.verbosity > 0:
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
    if s.verbosity > 0:
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
    if s.verbosity > 0:
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
    if s.verbosity > 0:
        logging.info(f"Bind sockets\t\t-> OK\t-> READ CONFIG")

    return states.READ_CONFIG

#******************************************************************************/
#* Errors-specific actions                                                    */
#******************************************************************************/

def parse_error(s: status):
    
    json_event_message = {
        "type": "error",
        "error": "Config parse error"
    }

    generic_publish_message(s, defaults_abcd_events_topic, json_event_message)

    if s.verbosity > 0:
        logging.info(f"Parse error\t\t-> OK\t-> CLOSE SOCKETS")

    return states.CLOSE_SOCKETS

def communication_error(s: status):
    
    json_event_message = {
        "type": "error",
        "error": "Communication error"
    }

    generic_publish_message(s, defaults_abcd_events_topic, json_event_message)

    if s.verbosity > 0:
        logging.info(f"Communication error\t-> OK\t-> CLOSE SOCKETS")

    return states.CLOSE_SOCKETS

def configure_error(s: status):
    
    json_event_message = {
        "type": "error",
        "error": "Configure error"
    }

    generic_publish_message(s, defaults_abcd_events_topic, json_event_message)

    if s.verbosity > 0:
        logging.info(f"Configure error\t\t-> OK\t-> DESTROY DIGITIZER")

    return states.DESTROY_DIGITIZER

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

    if s.verbosity > 0:
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

    if s.verbosity > 0:
        logging.info(f"Destroy context\t\t-> OK\t-> STOP")

    return states.STOP
