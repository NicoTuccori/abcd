# -----------------------------------------------------------------------------
# This file is part of ABCD.
# 2025 Nicolò Tuccori
# -----------------------------------------------------------------------------

"""
Actions to interface and read PETsys TOFPET2 ASICs
Python-version of standard ABCD actions
"""

import zmq, json, time
import numpy as np
from datetime import datetime
import logging
import copy
from .library import send_byte_message, receive_byte_message, parse_events, decode_temp_sensor, receive_json_message_no_topic, send_json_message, EVENT_SIZE
from .typedefs import status, PlotType
from .timeseries import TimeSeries
from . import states

import os

# Define or import your delay constant (ms)
defaults_abcd_zmq_delay = 100  # replace with actual constant if needed
defaults_abcd_events_topic = "events_abcd"
defaults_abcd_data_events_topic = "events_abcd"
defaults_abcd_status_topic = "status_abcd"
defaults_abcd_publish_timeout = 10
defaults_abcd_temp_publish_timeout = 30

#******************************************************************************/
#* Generic actions                                                            */
#******************************************************************************/

def generic_publish_message(s: status, topic: str, status_message: dict):
    
    s.update_timestamp()
    status_message["module"] = "spect"
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

# def generic_publish_events(s: status):
    
#     buffer_size = len(s.events_buffer) // EVENT_SIZE
#     data_size = len(s.events_buffer)

#     if buffer_size == 0:
#         return

#     topic = f"{defaults_abcd_events_topic}_v0_n{s.events_msg_ID}_s{data_size}"

#     if s.verbosity > 0:
#         logging.info(f"Sending binary buffer; "
#                      f"Topic: {topic}; events: {buffer_size}; buffer size: {data_size};")

#     result = send_byte_message(
#         socket=s.data_socket,
#         topic=topic,
#         buffer_bytes=s.events_buffer,  # bytearray is already bytes-like
#         verbosity=s.verbosity,
#     )

#     s.events_msg_ID += 1

#     if not result:
#         logging.warning(f"ZeroMQ Error publishing events")

#     # Reset buffer
#     s.events_buffer.clear()
#     # s.events_buffer.reserve = s.events_buffer_max_size * EVENT_SIZE

# def generic_read_configfile(s: status) -> bool:
    
#     if s.verbosity > 0:
#         logging.info(f"Reading config file: {s.spect_config_file}")

#     try:
#         with open(s.spect_config_file, 'r') as f:
#             new_config = json.load(f)
#     except json.JSONDecodeError as e:
#         logging.error(f"Parse error while reading config file: {e.msg} "
#               f"(line: {e.lineno}, column: {e.colno})")
#         return False
#     except FileNotFoundError:
#         logging.error(f"Config file not found: {s.spect_config_file}")
#         return False
#     except Exception as e:
#         logging.error(f"Unexpected error reading config file: {e}")
#         return False

#     s.spect_config = new_config

#     return True

def generic_read_socket(s: status) -> bool:

    abcd_data_socket = s.abcd_data_socket

    try:
        topic, input_buffer, size = receive_byte_message(abcd_data_socket, True, s.verbosity)
    except Exception as e:
        logging.error(f"ZeroMQ Error on receive: {e}")
        return False

    if size is None:
        logging.info(f"No message received on ZeroMQ socket.")
        return False

    while size > 0:
        if s.verbosity > 0:
            logging.info(f"Message size: {size};")
            logging.info(f"Topic: {topic};")

        if topic.startswith(defaults_abcd_data_events_topic):
            event_start = time.time()

            data_size = size
            event_size = EVENT_SIZE
            events_number = data_size // event_size

            if s.verbosity > 0:
                logging.info(f"Data size: {data_size}; Events number: {events_number}; mod: {data_size % event_size};")

            events = list(parse_events(input_buffer))
            events_number = len(events)

            for i, event in enumerate(events):

                ts = event['timestamp']
                if s.start_timestamp is None:
                    s.start_timestamp = ts
                t = ts - s.start_timestamp

                if s.plot_type == PlotType.ABTP2_TEMPERATURE:
                    channel = event['baseline']
                    label = decode_temp_sensor(channel)
                    y = round(event['qshort']/100,2)

                    if s.verbosity > 0:
                        logging.info(f"Event: {i}; Channel: {channel}; Sensor: {label}; time: {ts}; y: {y};")

                if channel not in s.active_channels:
                    s.active_channels.append(channel)
                    s.channel_labels.append(label)
                    s.plots_t.append(TimeSeries(s.verbosity))

                s.plots_t[channel].add_point(ts, t, y)

            event_stop = time.time()

            if s.verbosity > 0:
                elapsed_ms = (event_stop - event_start) * 1000
                speed_MBps = data_size / elapsed_ms * 1000 / 1024 / 1024
                rate_evts = events_number / elapsed_ms * 1000

                logging.info(f"Events number: {events_number}; Elaboration time: {elapsed_ms:.2f} ms; "
                      f"Speed: {speed_MBps:.2f} MB/s, {rate_evts:.2f} evts/s;")

        topic, input_buffer, size = receive_byte_message(abcd_data_socket, s.verbosity)

    return True

def generic_publish_data(s: status):

    status_message = {}
    active_channels = []
    channels_data = []

    now = time.time()
    pubtime = now - s.last_publication
    if pubtime <= 0:
        pubtime = 1e-6  # prevent division by zero

    for channel in s.active_channels:
        plot_t = s.plots_t[channel]

        if not plot_t.isempty():

            if s.verbosity > 0:
                logging.info(f"Publishing data for channel: {channel}")

            plot_t_data = plot_t.to_json()

            channel_data = {
                "id": channel,
                "enabled": True,
                "label": s.channel_labels[channel],
                "plot": plot_t_data
            }
            
            channels_data.append(channel_data)
            active_channels.append(channel)

    status_message["data"] = channels_data
    status_message["active_channels"] = active_channels
    status_message["module"] = "spect"
    status_message["timestamp"] = datetime.now().isoformat()
    status_message["msg_ID"] = s.data_msg_ID

    try:
        send_json_message(
            s.data_socket,
            "spect.plots",
            status_message,
            s.verbosity
        )
    except Exception as e:
        logging.error(f"Failed to send data: {e}")
        return False
    
    s.data_msg_ID += 1
    s.last_publication = now

    return True

#******************************************************************************/
#* Specific actions                                                   */
#******************************************************************************/

def read_config(s: status):
    
    # TO DO

    if s.verbosity > 0:
        logging.info(f"Read config\t\t-> OK\t-> PUBLISH STATUS")

    return states.PUBLISH_STATUS
    # return states.APPLY_CONFIG TO DO

def publish_status(s: status):

    status_message = {
        "statuses": [],
        "active_channels": [],
        "config": s.spect_config
    }

    # Publish the message using the generic publisher
    generic_publish_message(
        s,
        defaults_abcd_status_topic,
        status_message
    )
    
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

        # --- reset ---
        if command == "reset" and "arguments" in json_message:
            arguments = json_message["arguments"]
            # TO DO
            pass
        
        # --- reconfigure ---
        elif command == "reconfigure" and "arguments" in json_message:
            arguments = json_message["arguments"]
            # TO DO
            pass

        elif command == "quit":
            return states.CLOSE_SOCKETS

    return states.READ_SOCKET

def read_socket(s: status):

    generic_read_socket(s)

    now = time.time()
    last_pub = s.last_publication
    if (now - last_pub) > defaults_abcd_publish_timeout:
        return states.PUBLISH_DATA

    return states.READ_SOCKET

def publish_data(s: status):
    
    success = generic_publish_data(s)

    if not success:
        logging.error("Failed to publish data")
        return states.PUBLISH_STATUS

    return states.PUBLISH_STATUS

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

    try:
        # Create the abcd data socket
        abcd_data_socket = context.socket(zmq.SUB)
    except Exception as e:
        logging.error(f"ZeroMQ Error on abcd data socket creation: {e}")
        return states.COMMUNICATION_ERROR

    # Assign sockets to status object
    s.status_socket = status_socket
    s.data_socket = data_socket
    s.commands_socket = commands_socket
    s.abcd_data_socket = abcd_data_socket

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

    try:
        s.abcd_data_socket.bind(s.abcd_data_address)
    except zmq.ZMQError as e:
        logging.error(f"ZeroMQ Error on abcd data socket binding: {e}")
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
    try_close_socket(s.abcd_data_socket, "abcd data")

    if s.verbosity > 0:
        logging.info(f"Close sockets\t\t-> OK\t-> DESTROY CONTEXT")

    return states.DESTROY_CONTEXT

#******************************************************************************/
#* Errors-specific actions                                                    */
#******************************************************************************/

def communication_error(s: status):
    
    json_event_message = {
        "type": "error",
        "error": "Communication error"
    }

    generic_publish_message(s, defaults_abcd_events_topic, json_event_message)

    if s.verbosity > 0:
        logging.info(f"Communication error\t-> OK\t-> CLOSE SOCKETS")

    return states.CLOSE_SOCKETS

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
