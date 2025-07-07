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

from .petsys_lib import daqd, config, fe_power

# Define or import your delay constant (ms)
defaults_abcd_zmq_delay = 100  # replace with actual constant if needed
defaults_abcd_events_topic = "events_abcd"
defaults_abcd_status_topic = "status_abcd"
defaults_abcd_publish_timeout = 10

#******************************************************************************/
#* Generic actions                                                            */
#******************************************************************************/

def generic_publish_message(s: status, topic: str, status_message: dict):
    
    s.update_timestamp()
    status_message["module"] = "abtp2"
    status_message["timestamp"] = s.last_publication
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
        if s.verbosity > 0:
            logging.info("DAQ daemon started successfully.")
    except Exception as e:
        logging.error(f"Failed to start DAQ daemon: {e}")
        return False

    try:
        s.connection = daqd.Connection()
        if s.verbosity > 0:
            logging.info("Established connection to DAQ daemon.")
    except Exception as e:
        logging.error(f"Failed to connect to DAQ daemon: {e}")
        return False
    
    HowIsDAQD = False
    try:
        HowIsDAQD = s.daemon.is_daqd_running()
        if HowIsDAQD:
            if s.verbosity > 0:
                logging.info("DAQ daemon running.")
        else:
            logging.error(f"Failed to find the DAQ daemon: HowIsDAQD = {HowIsDAQD}")
            return False
    except Exception as e:
        logging.error(f"Failed to check if DAQ daemon is running: {e}")
        return False

    try:
        if (s.abcd_config["portID"] != None and s.abcd_config["slaveID"] != None):
            for p, s in s.connection.getActiveFEBDs():
                fe_power.set_fem_power(s.connection,p,s,"off")  
            s.connection.initializeSystem(power_lst = [(s.abcd_config["portID"], s.abcd_config["slaveID"])])
        else:
            s.connection.initializeSystem()
    except Exception as e:
        logging.error(f"Failed to initialise system: {e}")
        return False

    return True

def generic_configure_digitizer(s: status) -> bool:

    if s.verbosity > 0:
        logging.info("Configuring digitizer")

    try:
        s.tp2_config.loadToHardware(s.connection, 
                                    bias_enable=config.APPLY_BIAS_OFF, 
                                    hw_trigger_enable=s.abcd_config["hwTrigger"], 
                                    qdc_mode = s.abcd_config["mode"])
        if s.verbosity > 0:
            logging.info("Configuration loaded to hardware")
    except Exception as e:
        logging.error(f"Error during loading configuration to hardware: {e}")
        return False

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

    s.abcd_config = new_config

    required_keys = {
        "config",
        "fileNamePrefix",
        "time",
        "mode",
        "hwTrigger",
        "enableOnlineProcessing",
        "outputType",
        "outputFormat",
        "writeFraction",
        "writeMultipleHits",
        "timeref",
        "writeRaw",
        "paramTable",
        "waitOn",
        "portID",
        "slaveID"
    }

    # Check for missing keys
    missing_keys = required_keys - s.abcd_config.keys()

    if missing_keys:
        logging.error("Missing keys in config file:")
        for key in sorted(missing_keys):
            logging.error(f" - {key}")
        return states.PARSE_ERROR
    else:
        if s.verbosity > 0:
            logging.info(f"All expected keys are present in {s.config_file}.")
    
    if os.path.isfile(os.path.join(s.working_folder, s.abcd_config["config"])):
        if s.verbosity > 0:
            logging.info(f"TOFPET2 config file found: {s.abcd_config['config']}")
        s.tp2_config_file = os.path.join(s.working_folder, s.abcd_config["config"])
    else:
        logging.error(f"TOFPET2 Config file missing")
        return states.PARSE_ERROR
    
    mask = config.LOAD_ALL
    if s.abcd_config["mode"] != "mixed":
        mask ^= config.LOAD_QDCMODE_MAP

    # Only for sw_daq_tofpet2 v2025.05.21
    # if not s.abcd_config["hwTrigger"]:
    #     mask ^= config.LOAD_FIRMWARE_QDC_CALIBRATION

    try:
        s.tp2_config = config.ConfigFromFile(s.tp2_config_file, loadMask=mask)
    except SystemExit as e:
        if e.code == 1:
            return states.PARSE_ERROR
    except Exception as e:
        logging.error(f"Error reading TOFPET2 config file {s.tp2_config_file}: {e}")
        return states.PARSE_ERROR

    if s.verbosity > 0:
        logging.info(f"Read config\t\t-> OK\t-> CREATE DIGITIZER")

    return states.CREATE_DIGITIZER

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
        # time.sleep(20)
        return states.CONFIGURE_DIGITIZER
        # return states.DESTROY_DIGITIZER
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

def configure_digitizer(s: status):
    
    success = generic_configure_digitizer(s)

    if success:
        return states.PUBLISH_STATUS
        # return states.CONFIGURE_ERROR
    else:
        return states.CONFIGURE_ERROR

def publish_status(s: status):

    HowIsDAQD = False
    try:
        HowIsDAQD = s.daemon.is_daqd_running()
        if HowIsDAQD:
            if s.verbosity > 0:
                logging.info("DAQ daemon running.")
        else:
            logging.error(f"Failed to find the DAQ daemon: HowIsDAQD = {HowIsDAQD}")
            # return states.DIGITIZER_ERROR
            return states.CONFIGURE_ERROR 
    except Exception as e:
        logging.error(f"Failed to check if DAQ daemon is running: {e}")
        # return states.DIGITIZER_ERROR
        return states.CONFIGURE_ERROR 

    # Build the status message as a nested dictionary
    status_message = {
        "config": json.loads(json.dumps(s.abcd_config)),
        "acquisition": {
            "running": False
        },
        "digitizer": {
            "valid_pointer": True,
            "active": True
        }
    }

    # Publish the message using the generic publisher
    generic_publish_message(
        s,
        defaults_abcd_status_topic,
        status_message
    )

    return states.RECEIVE_COMMANDS

def receive_commands(s: status):

    commands_socket = s.commands_socket

    try:
        # Non-blocking receive; adjust flags if needed for blocking or timeout
        topic, msg_bytes = commands_socket.recv_multipart(flags=zmq.NOBLOCK)
    except zmq.Again:
        # No message received
        msg_bytes = None

    if msg_bytes is not None:
        size = len(msg_bytes)
        if s.verbosity > 0:
            logging.info("Received message; size: {size}")

        try:
            message_str = msg_bytes.decode("utf-8")
            if s.verbosity > 0:
                logging.info("Message buffer: {message_str}")

            json_message = json.loads(message_str)
        except json.JSONDecodeError as e:
            logging.error("ERROR: JSON decode error: {e}")
            json_message = None

        if json_message:
            command_ID = json_message.get("msg_ID", None)
            command = json_message.get("command", "")
            arguments = json_message.get("arguments", None)

            if s.verbosity > 0:
                logging.info("Command ID: {command_ID}")

            if command == "start":
                logging.info("### Start acquisition command received ###")
                return states.START_ACQUISITION

            elif command == "reconfigure" and arguments:
                new_config = arguments.get("config", None)
                if new_config:
                    # Replace global config
                    s.config = new_config  # Assuming dict or JSON-like

                    # Publish event about reconfiguration
                    event_msg = {
                        "type": "event",
                        "event": "Digitizer reconfiguration",
                    }
                    generic_publish_message(s, defaults_abcd_events_topic, event_msg)

                    return states.CONFIGURE_DIGITIZER

            elif command == "off":
                # return states.CLEAR_MEMORY
                return states.DESTROY_DIGITIZER

            elif command == "quit":
                # return states.CLEAR_MEMORY
                return states.DESTROY_DIGITIZER

    # Check if we need to publish status due to timeout
    now = time.time()
    last_pub = s.last_publication
    if (now - last_pub) > defaults_abcd_publish_timeout:
        return states.PUBLISH_STATUS

    # Default: keep receiving commands
    return states.RECEIVE_COMMANDS

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
