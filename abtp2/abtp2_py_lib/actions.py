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
import threading
import copy
import shutil
from .library import send_byte_message, receive_json_message_no_topic, EVENT_SIZE
from .typedefs import status, daqd_daemon
from . import states

import os

from .petsys_lib import daqd, config, fe_power, fe_temperature

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

    message = json.dumps(status_message, separators=(",", ":"))

    total_size = len(message)
    topic = f"{topic}_v0_s{total_size}"

    if s.verbosity > 0:
        logging.info(f"Sending status message; Topic: {topic}; "
                     f"Size: {total_size}; Message: {message}")

    success = send_byte_message(
        socket=s.status_socket,
        topic=topic,
        buffer_bytes=message.encode("utf-8"),
        verbosity=s.verbosity
    )

    if not success:
        logging.warning("Message failed to send on ZeroMQ socket.")

    s.status_msg_ID += 1

def generic_publish_events(s: status, topic: str, status_message: dict):
    
    buffer_size = len(s.events_buffer) // EVENT_SIZE
    data_size = len(s.events_buffer)

    if buffer_size == 0:
        return

    topic = f"{defaults_abcd_events_topic}_v0_n{s.events_msg_ID}_s{data_size}"

    if s.verbosity > 0:
        logging.info(f"Sending binary buffer; "
                     f"Topic: {topic}; events: {buffer_size}; buffer size: {data_size};")

    result = send_byte_message(
        socket=s.data_socket,
        topic=topic,
        buffer_bytes=s.events_buffer,  # bytearray is already bytes-like
        verbosity=s.verbosity,
    )

    s.events_msg_ID += 1

    if not result:
        logging.warning(f"ZeroMQ Error publishing events")

    # Reset buffer
    s.events_buffer.clear()
    # s.events_buffer.reserve = s.events_buffer_max_size * EVENT_SIZE

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
        time.sleep(5)
    except Exception as e:
        logging.error(f"Failed to start DAQ daemon: {e}")
        return False

    try:
        s.connection = daqd.Connection()
        if s.verbosity > 0:
            logging.info("Established connection to DAQ daemon.")
        time.sleep(5)
    except Exception as e:
        logging.error(f"Failed to connect to DAQ daemon: {e}")
        return False
    
    HowIsDAQD = False
    try:
        HowIsDAQD = s.daemon.is_daqd_running()
        if HowIsDAQD:
            if s.verbosity > 0:
                logging.info("DAQ daemon running.")
            time.sleep(1)
        else:
            logging.error(f"Failed to find the DAQ daemon: HowIsDAQD = {HowIsDAQD}")
            return False
    except Exception as e:
        logging.error(f"Failed to check if DAQ daemon is running: {e}")
        return False

    return True

def generic_read_configfile(s: status) -> bool:
    
    if s.verbosity > 0:
        logging.info(f"Reading config file: {s.abcd_config_file}")

    try:
        with open(s.abcd_config_file, 'r') as f:
            new_config = json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Parse error while reading config file: {e.msg} "
              f"(line: {e.lineno}, column: {e.colno})")
        return False
    except FileNotFoundError:
        logging.error(f"Config file not found: {s.abcd_config_file}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error reading config file: {e}")
        return False

    s.abcd_config = new_config

    return True

def generic_check_and_load_config(s: status) -> bool:

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
        return False
    else:
        if s.verbosity > 0:
            logging.info(f"All expected keys are present.")
    
    if os.path.isfile(os.path.join(s.working_folder, s.abcd_config["config"])):
        s.tp2_config_file = os.path.join(s.working_folder, s.abcd_config["config"])
        if s.verbosity > 0:
            logging.info(f"TOFPET2 config file found: {s.tp2_config_file}")
    else:
        logging.error(f"TOFPET2 Config file missing")
        return False
    
    if not os.path.exists(os.path.join(s.working_folder, "bias_settings.tsv")):
        logging.error(f"Please save bias voltage settings in {s.working_folder} as bias_settings.tsv.")
        return False

    if not os.path.exists(os.path.join(s.working_folder, "disc_settings.tsv")):
        logging.error(f"Please save threshold settings in {s.working_folder} as disc_settings.tsv.")
        return False
    
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
            return False
    except Exception as e:
        logging.error(f"Error reading TOFPET2 config file {s.tp2_config_file}: {e}")
        return False
    
    return True

def generic_configure_digitizer(s: status) -> bool:

    if s.verbosity > 0:
        logging.info("Initialising digitizer")

    try:
        if (s.abcd_config["portID"] != None and s.abcd_config["slaveID"] != None):
            for p, s in s.connection.getActiveFEBDs():
                fe_power.set_fem_power(s.connection,p,s,"off")
                time.sleep(0.01)
            s.connection.initializeSystem(power_lst = [(s.abcd_config["portID"], s.abcd_config["slaveID"])])
        else:
            s.connection.initializeSystem()
        time.sleep(1)
    except Exception as e:
        logging.error(f"Failed to initialise system: {e}")
        return False
    
    try:
        s.sensor_list = fe_temperature.get_sensor_list(s.connection, debug=s.verbosity)
        if not s.sensor_list:
            logging.error("No temperature sensors found. Check FEM connections and power.")
            return False
        else:
            s.sensor_list.sort(key = lambda x:x.get_location())
            if s.verbosity > 0:
                for sensor in s.sensor_list: 
                    logging.info(f"Found temperature sensor at {sensor.get_location()}: {sensor.get_temperature()} ºC")
    except Exception as e:
        logging.error(f"Failed to get temperature sensors: {e}")
        return False

    if s.verbosity > 0:
        logging.info("Configuring digitizer")

    try:
        s.tp2_config.loadToHardware(s.connection, 
                                    bias_enable=config.APPLY_BIAS_OFF, 
                                    hw_trigger_enable=s.abcd_config["hwTrigger"], 
                                    qdc_mode = s.abcd_config["mode"])
        if s.verbosity > 0:
            logging.info("Configuration loaded to hardware")
        time.sleep(1)
    except Exception as e:
        logging.error(f"Error during loading configuration to hardware: {e}")
        return False

    return True

def generic_destroy_digitizer(s: status) -> None:

    if s.verbosity > 0:
        logging.info("Destroying digitizer")
        logging.info("Shutting down DAQ daemon")

    try:
        for portID, slaveID in s.connection.getActiveFEBDs(): 
            if fe_power.get_bias_power_status(s.connection, portID, slaveID):
                fe_power.set_bias_power(s.connection, portID, slaveID, "off")
                time.sleep(0.01)
            if fe_power.get_fem_power_status(s.connection, portID, slaveID):
                fe_power.set_fem_power(s.connection, portID, slaveID, "off")
                time.sleep(0.01)
        if s.verbosity > 0:
            logging.info("SiPM bias OFF & FEM OFF")
    except:
        logging.error(f"Error while turning SiPM and FEM OFF. ATTENTION!")

    try:
        s.daemon.stop()
    except Exception as e:
        logging.error(f"Error during shutdown: {e}")

    # TO DO

def generic_stop_acquisition(s: status) -> None:

    if s.verbosity > 0:
        logging.info(f"#### Stopping acquisition!!!")
    try:
        for portID, slaveID in s.connection.getActiveFEBDs(): 
            if fe_power.get_bias_power_status(s.connection, portID, slaveID):
                fe_power.set_bias_power(s.connection, portID, slaveID, "off")
                time.sleep(0.01)
        if s.verbosity > 0:
            logging.info("SiPM bias OFF")
        time.sleep(1)
    except Exception as e:
        logging.error(f"Error during turning SiPM bias off: {e}. ATTENTION!")

    try:
        s.connection.stopAcquisition()
        time.sleep(1)
    except Exception as e:
        logging.error(f"Error during stop acquisition: {e}")

    # Record stop time and compute duration
    stop_time = time.time()
    delta_time = int(stop_time - s.start_time)

    s.stop_time = stop_time

    if s.verbosity > 0:
        print(f"Run time: {delta_time}")

def generic_acquisition_thread(s: status) -> None:

    def _make_progress_cb(s):
        # throttle + dedup
        last_frames    = -1        # force first publish
        last_pub_wall  = -1.0
        min_interval   = getattr(s, "status_pub_interval", 1.0)  # seconds

        def progress_cb(frames, wall_time, data_time, nEvents, nFramesLost):
            nonlocal last_frames, last_pub_wall

            # guard: frames must advance
            if frames <= last_frames:
                return

            # guard: time throttle
            if last_pub_wall >= 0 and (wall_time - last_pub_wall) < min_interval:
                return

            last_frames   = frames
            last_pub_wall = wall_time

            generic_acquisition_publish_status(s, frames, wall_time, data_time, nEvents, nFramesLost)

        return progress_cb

    s.connection.acquire(
        s.abcd_config["time"],
        0,
        0,
        progress_callback=_make_progress_cb(s)
    )

def generic_acquisition_publish_status(s: status, frames, wall_time, data_time, nEvents, nFramesLost) -> None:
    
    status_message = {}

    status_message["config"] = s.abcd_config

    status_message["digitizer"] = {}
    status_message["acquisition"] = {}

    HowIsDAQD = False
    HowIsDAQD = s.daemon.is_daqd_running()

    if not HowIsDAQD:
        
        logging.error(f"Failed to find the DAQ daemon: HowIsDAQD = {HowIsDAQD}")
        status_message["digitizer"]["valid_pointer"] = False
        status_message["acquisition"]["running"] = False

    else:

        status_message["digitizer"]["valid_pointer"] = True
        status_message["digitizer"]["active"] = HowIsDAQD
        status_message["acquisition"]["running"] = True

        now = time.time()
        runtime = int(now - s.start_time) if hasattr(s, "start_time") else 0
        status_message["acquisition"]["runtime"] = runtime

        # Calculate elapsed time since last publication
        pub_delta = (now - s.last_publication) if hasattr(s, "last_publication") else None
        pubtime = pub_delta if pub_delta and pub_delta > 0 else 1e-3  # avoid division by zero

        # Fill in acquisition progress from callback arguments
        status_message["acquisition"]["frames"] = frames
        status_message["acquisition"]["events"] = nEvents
        status_message["acquisition"]["frames_lost"] = nFramesLost
        status_message["acquisition"]["wall_time"] = wall_time
        status_message["acquisition"]["data_time"] = data_time
        status_message["acquisition"]["delay"] = (wall_time - data_time) if (wall_time is not None and data_time is not None) else None

    # Debugging
    if s.verbosity > 0:
        logging.debug(f"Publishing status message: {status_message}")

    # Publish the message over ZMQ or your messaging system
    generic_publish_message(s, defaults_abcd_status_topic, status_message)

#******************************************************************************/
#* Digitizer-specific actions                                                   */
#******************************************************************************/

def read_config(s: status):
    
    success = generic_read_configfile(s)

    if not success:
        logging.error(f"Failed to read configs from file {s.abcd_config_file}")
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
    else:
        logging.error("Digitizer creation failed")
        return states.DIGITIZER_ERROR
    
def destroy_digitizer(s: status):

    json_event_message = {
        "type": "event",
        "event": "Digitizer deactivation"
    }

    generic_publish_message(s, defaults_abcd_events_topic, json_event_message)

    generic_destroy_digitizer(s)

    return states.CLOSE_SOCKETS

def configure_digitizer(s: status):
    
    success = generic_check_and_load_config(s)

    if not success:
        logging.error("Failed to check and load config")
        return states.CONFIGURE_ERROR

    success = generic_configure_digitizer(s)

    if success:
        if s.verbosity > 0:
            logging.info("Configure digitizer\t-> OK\t-> PUBLISH_STATUS")
        return states.PUBLISH_STATUS
    else:
        logging.error("Configure digitizer failed")
        return states.CONFIGURE_ERROR

def publish_status(s: status):

    status_message = {
        "config": json.loads(json.dumps(s.abcd_config)),
        "acquisition": {
            "running": False
        },
        "digitizer": {}  
    }

    HowIsDAQD = False
    try:
        HowIsDAQD = s.daemon.is_daqd_running()
        if HowIsDAQD:
            if s.verbosity > 0:
                logging.info("DAQ daemon running.")
            status_message["digitizer"]["valid_pointer"] = True
            status_message["digitizer"]["active"] = True
        else:
            logging.error(f"Failed to find the DAQ daemon: HowIsDAQD = {HowIsDAQD}")
            status_message["digitizer"]["valid_pointer"] = False
    except Exception as e:
        logging.error(f"Failed to check if DAQ daemon is running: {e}")
        # return states.DIGITIZER_ERROR
        return states.CONFIGURE_ERROR 

    # Publish the message using the generic publisher
    generic_publish_message(
        s,
        defaults_abcd_status_topic,
        status_message
    )

    if not HowIsDAQD:
        # return states.DIGITIZER_ERROR
        return states.CONFIGURE_ERROR 
    else:
        if s.verbosity > 0:
            logging.info("Publish status\t\t-> OK\t-> RECEIVE_COMMANDS")
        return states.RECEIVE_COMMANDS

def receive_commands(s: status):

    commands_socket = s.commands_socket

    try:
        json_message = receive_json_message_no_topic(commands_socket,verbosity=s.verbosity)
        if s.verbosity > 0 and json_message:
            logging.info(f"Received message: {json_message}")
    except Exception as e:
        logging.error(f"Failed to receive commands: {e}")
        return states.RECEIVE_COMMANDS

    if json_message:

        command = json_message.get("command")
        if not isinstance(command, str):
            try:
                command = str(command)
            except Exception:
                command = None

        if s.verbosity > 0:
            logging.info(f"Message command: {command}")

        # --- start ---
        if command == "start":
            logging.info(f"################################################################### Start!!! ###")
            return states.START_ACQUISITION
        
        # --- reconfigure ---
        elif command == "reconfigure" and "arguments" in json_message:
            arguments = json_message["arguments"]

            if "config" in arguments:
                # Update global status config (deep copy in case caller mutates later)
                s.abcd_config = copy.deepcopy(arguments["config"])

                # Build and publish event
                event_message = {
                    "type": "event",
                    "event": "Digitizer reconfiguration",
                }
                generic_publish_message(s, defaults_abcd_events_topic, event_message)

                return states.CONFIGURE_DIGITIZER
            else:
                logging.error("Reconfigure command received, but no config provided")
                return states.RECEIVE_COMMANDS

        # --- stop ---
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

def start_acquisition(s: status):

    json_event_message = {
        "type": "event",
        "event": "Start acquisition"
    }

    generic_publish_message(s, defaults_abcd_events_topic, json_event_message)

    HowIsDAQD = False
    try:
        HowIsDAQD = s.daemon.is_daqd_running()
        if HowIsDAQD:
            if s.verbosity > 0:
                logging.info("DAQ daemon running.")
        else:
            logging.error(f"Failed to find the DAQ daemon: HowIsDAQD = {HowIsDAQD}")
            return states.DIGITIZER_ERROR
    except Exception as e:
        logging.error(f"Failed to check if DAQ daemon is running: {e}")
        return states.DIGITIZER_ERROR
    
    try:
        for portID, slaveID in s.connection.getActiveFEBDs(): 
            fe_power.set_bias_power(s.connection, portID, slaveID, "on")
            time.sleep(0.01)
        if s.verbosity > 0:
            logging.info("SiPM bias ON")
    except:
        logging.error(f"Error during turning SiPM bias on")
        return states.DIGITIZER_ERROR
    
    # try:
    s.connection.openRawAcquisition(s.abcd_config["fileNamePrefix"])
    # except:
    #     logging.error(f"Error during opening raw acquisition. Check {s.abcd_config['fileNamePrefix']}")
    #     return states.DIGITIZER_ERROR
    
    try:
        activeAsics = s.connection.getActiveAsics()
        activeChannels = [ (portID, slaveID, chipID, channelID) for channelID in range(64) for portID, slaveID, chipID in activeAsics ]

        asicsConfig = s.connection.getAsicsConfig()
    except:
        logging.error(f"Error retrieving active channels and asics configuration")
        return states.ACQUISITION_ERROR

    if getattr(s, "acquisition_thread", None) and s.acquisition_thread.is_alive():
        logging.error("Acquisition thread is already running")
        return states.ACQUISITION_RECEIVE_COMMANDS
    
    if s.abcd_config["paramTable"] is None:
        try:
            s.acquisition_thread = threading.Thread(
                target=generic_acquisition_thread,
                args=(s,),
                daemon=True
            )
            s.acquisition_thread.start()
        except Exception as e:
            logging.error(f"Start of acquisition thread failed: {e}")
            return states.ACQUISITION_ERROR
    else:
        # TO DO FOR PARAM SCANS
        True

    if s.verbosity > 0:
        logging.info("Copying config file")
    
    # # Copy config files
    # shutil.copyfile(s.working_folder + "/abcd_config.tsv", s.working_folder + "/" + s.fileNamePrefix + "_abcd_config.tsv")
    # shutil.copyfile(s.working_folder + "/disc_settings.tsv", s.working_folder + "/" + s.fileNamePrefix + "_disc_settings.tsv")
    # shutil.copyfile(s.working_folder + "/map_channel.tsv", s.abcd_config["fileNamePrefix"] + "_map_channel.tsv")
    # shutil.copyfile(s.working_folder + "/map_trigger.tsv", s.abcd_config["fileNamePrefix"] + "_map_trigger.tsv")
    # shutil.copyfile(s.working_folder + "/config.ini", s.abcd_config["fileNamePrefix"] + "_config.ini")

    s.start_time = time.time()
    
    return states.ACQUISITION_RECEIVE_COMMANDS

def acquisition_receive_commands(s: status):

    commands_socket = s.commands_socket

    try:
        json_message = receive_json_message_no_topic(commands_socket,verbosity=s.verbosity)
        if s.verbosity > 0:
            logging.info(f"Received message: {json_message}")
    except Exception as e:
        logging.error(f"Failed to receive commands: {e}")
        return states.RECEIVE_COMMANDS

    if json_message:

        command = json_message.get("command")
        if not isinstance(command, str):
            try:
                command = str(command)
            except Exception:
                command = None

        if s.verbosity > 0:
            logging.info(f"Message command: {command}")

        if command == "stop":
            logging.info("################################################################### Stop!!! ###")
            return states.STOP_ACQUISITION
        else:
            logging.error(f"Recevied command: {command}. It is either unknown or not allowed during acquisition.")

    return states.POOL_DIGITIZER

def pool_digitizer(s: status):

    thread = getattr(s, "acquisition_thread", None)

    if thread and thread.is_alive():
        return states.ACQUISITION_RECEIVE_COMMANDS
    
    else:
        if s.verbosity > 0:
            logging.info("The acquisition is finished. Stopping...")
        return states.STOP_ACQUISITION
    
def stop_acquisition(s: status):

    generic_stop_acquisition(s)

    # Compute duration in seconds
    delta_time = int((s.stop_time - s.start_time))
    event_message = f"Stop acquisition (duration: {delta_time} s)"

    # Create event JSON and publish
    event_json = {
        "type": "event",
        "event": event_message
    }

    generic_publish_message(s, defaults_abcd_events_topic, event_json)

    HowIsDAQD = False
    try:
        HowIsDAQD = s.daemon.is_daqd_running()
        if HowIsDAQD:
            if s.verbosity > 0:
                logging.info("DAQ daemon running.")
            time.sleep(1)
        else:
            logging.error(f"Failed to find the DAQ daemon: HowIsDAQD = {HowIsDAQD}")
            return states.DIGITIZER_ERROR
    except Exception as e:
        logging.error(f"Failed to check if DAQ daemon is running: {e}")
        return states.DIGITIZER_ERROR

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

def digitizer_error(s: status):
    
    json_event_message = {
        "type": "error",
        "error": "Digitizer error"
    }

    generic_publish_message(s, defaults_abcd_events_topic, json_event_message)

    try:
        for portID, slaveID in s.connection.getActiveFEBDs():
            if fe_power.get_bias_power_status(s.connection, portID, slaveID):
                fe_power.set_bias_power(s.connection, portID, slaveID, "off")
                time.sleep(0.01)
        if s.verbosity > 0:
            logging.info("SiPM bias OFF")
    except:
        logging.error(f"Error during turning SiPM bias off. ATTENTION!")

    if s.verbosity > 0:
        logging.info(f"Digitizer error\t\t-> OK\t-> DESTROY DIGITIZER")

    return states.DESTROY_DIGITIZER

def acquisition_error(s: status):
    
    json_event_message = {
        "type": "error",
        "error": "Acquisition error"
    }

    generic_publish_message(s, defaults_abcd_events_topic, json_event_message)

    try:
        for portID, slaveID in s.connection.getActiveFEBDs(): 
            if fe_power.get_bias_power_status(s.connection, portID, slaveID):
                fe_power.set_bias_power(s.connection, portID, slaveID, "off")
                time.sleep(0.01)
        if s.verbosity > 0:
            logging.info("SiPM bias OFF")
    except:
        logging.error(f"Error during turning SiPM bias off. ATTENTION!")

    if s.verbosity > 0:
        logging.info(f"Acquisition error\t\t-> OK\t-> DESTROY DIGITIZER")

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
