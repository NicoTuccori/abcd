# -----------------------------------------------------------------------------
# This file is part of ABCD.
# 2025 Nicolò Tuccori
# -----------------------------------------------------------------------------

"""
Python-version of the functions defined in abcd/src/socket_functions.cpp
"""

import zmq
import sys
import json
import time
import logging
import struct

# ABCD event struct
# Little-endian like typical C++ on x86 (adjust '<' to '>' for big-endian if needed)
EVENT_STRUCT = struct.Struct('<QHHHBB')  # Q=uint64, H=uint16, H=uint16, H=uint16, B=uint8, B=uint8
EVENT_SIZE = EVENT_STRUCT.size  # should be 16 bytes

def time_string():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def pack_event(timestamp: int, qshort: int, qlong: int, baseline: int, channel: int, group_counter: int) -> bytes:
    return EVENT_STRUCT.pack(timestamp, qshort, qlong, baseline, channel, group_counter)

def parse_events(buffer: bytes):
    """Yield events from a raw binary buffer."""
    for i in range(0, len(buffer), EVENT_SIZE):
        chunk = buffer[i:i + EVENT_SIZE]
        if len(chunk) < EVENT_SIZE:
            break  # incomplete event
        timestamp, qshort, qlong, baseline, channel, group_counter = EVENT_STRUCT.unpack(chunk)
        yield {
            'timestamp': timestamp,
            'qshort': float(qshort),
            'qlong': float(qlong),
            'baseline': float(baseline),
            'channel': channel,
            'group_counter': group_counter
        }

def encode_temp_sensor(portID: int, slaveID: int, moduleID: int, sensorID: int, sensorPlace: str) -> int:
    kind = 1 if sensorPlace == 'sipm' else 0
    return ((portID & 0x07) << 13) | \
           ((slaveID & 0x07) << 10) | \
           ((moduleID & 0x0F) << 6) | \
           ((sensorID & 0x07) << 3) | \
           (kind & 0x01)

def decode_temp_sensor(encoded: int):
    kind = encoded & 0x01
    sensorID = (encoded >> 3) & 0x07
    moduleID = (encoded >> 6) & 0x0F
    slaveID = (encoded >> 10) & 0x07
    portID = (encoded >> 13) & 0x07
    sensorPlace = 'sipm' if kind == 1 else 'other'
    
    return {
        'portID': portID,
        'slaveID': slaveID,
        'moduleID': moduleID,
        'sensorID': sensorID,
        'sensorPlace': sensorPlace
    }

def send_byte_message(socket: zmq.Socket,
                      topic: bytes,
                      buffer_bytes: bytes,
                      verbosity: int = 0) -> bool:
    """
    Send a raw byte message over a ZeroMQ socket, optionally prefixed by a topic + space.

    Args:
        socket (zmq.Socket): Destination ZeroMQ socket (e.g., PUB, PUSH, etc.).
        topic (str): Topic prefix. If non-empty, a trailing space is appended before the payload.
        buffer_bytes (bytes | bytearray | memoryview): Raw payload.
        verbosity (int): >0 prints debug info.

    Returns:
        bool: True on (apparent) success, False on error.
    """

    # Normalize topic (append space if non-empty)
    if topic:
        topic_with_space = topic + " "
    else:
        topic_with_space = ""

    # Ensure bytes payload
    try:
        payload = bytes(buffer_bytes)  # safe copy / conversion
    except Exception as e:
        logging.error(f"Error converting payload to bytes: {e}")
        return False
    
    topic_bytes = topic_with_space.encode("utf-8")
    frame = topic_bytes + payload
    envelope_size = len(frame)

    if verbosity > 0:
        logging.info(f"Message size: {envelope_size}")

    # Send
    try:
        #pyzmq's send() returns None on success; will raise ZMQError on failure.
        socket.send(frame, flags=0)
    except zmq.ZMQError as e:
        logging.error(f"ZeroMQ Error on send: {e}")
        return False

    return True

# From src/socket_functions.cpp
# def receive_byte_message(socket: zmq.Socket, extract_topic: bool = True, verbosity: int = 0):
#     """
#     Non-blocking receive of a raw byte message from a ZeroMQ socket.

#     Args:
#         socket (zmq.Socket): The ZeroMQ socket to read from.
#         verbosity (int): >0 enables debug prints.

#     Returns:
#         bytes: The received message payload, or empty bytes if no message or error.
#     """
#     try:
#         # Non-blocking receive
#         message = socket.recv(flags=zmq.DONTWAIT)
#     except zmq.Again:
#         # No message available
#         return b""
#     except zmq.ZMQError as e:
#         logging.error(f"ZeroMQ Error on receive: {e}")
#         return b""

#     if verbosity > 0:
#         logging.info(f"Message length: {len(message)}")

#     return message

# From include/socket_functions.h, same as used by spec
def receive_byte_message(socket, extract_topic=False, verbosity=0):
    """
    Receive a message from a ZeroMQ socket.

    Parameters:
        socket         -- ZeroMQ socket (zmq.Socket)
        extract_topic  -- If True, extract topic from message (bool)
        verbosity      -- Debug output level (int)

    Returns:
        (success, topic, data):
            success     -- True if successful or no message; False if error
            topic       -- topic string if extracted, else None
            data        -- byte string of data (excluding topic if extracted), else None
    """
    try:
        message = socket.recv(flags=zmq.DONTWAIT)
    except zmq.Again:
        # No message received (EAGAIN)
        return True, None, None
    except zmq.ZMQError as e:
        if verbosity > 0:
            print(f"ERROR: ZeroMQ Error on receive: {e}")
        return False, None, None

    if verbosity > 0:
        print(f"Message size: {len(message)}")

    topic = None
    data = None

    if extract_topic:
        separator_index = message.find(b' ')
        if separator_index == -1:
            if verbosity > 0:
                print("ERROR: Unable to find topic separator")
            return False, None, None

        topic_bytes = message[:separator_index]
        data = message[separator_index + 1:]

        try:
            topic = topic_bytes.decode('utf-8')
        except UnicodeDecodeError:
            if verbosity > 0:
                print("ERROR: Topic is not valid UTF-8")
            return False, None, None

        if verbosity > 0:
            print(f"Topic size: {len(topic)}; Data size: {len(data)}")
    else:
        data = message

    return True, topic, data

def receive_json_message_no_topic(socket, verbosity=0):
    """
    Non-blocking receive of a JSON message from a ZeroMQ socket.

    Args:
        socket (zmq.Socket): Socket to read from.
        verbosity (int): >0 prints debug info.

    Returns:
        dict: Parsed JSON object, or {} if no message / error / parse failure.
    """
    try:
        # Non-blocking receive (raw bytes)
        raw = socket.recv(flags=zmq.DONTWAIT)
    except zmq.Again:
        # No message available
        return {}
    except zmq.ZMQError as e:
        logging.error(f"ZeroMQ Error on receive: {e}")
        return {}

    # Decode as UTF-8 text (C++ code assumes char* -> string)
    try:
        message = raw.decode("utf-8", errors="replace")
    except Exception as e:
        logging.error(f"Error decoding message bytes: {e}")
        return {}

    if verbosity > 0:
        # The C++ prints message, length, recv result, and msg_size (same in Python len(raw))
        logging.info(f"Message: '{message}' length: {len(message)}, {len(raw)}, {len(raw)}")

    # Parse JSON
    try:
        json_message = json.loads(message)
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}")
        return {}

    return json_message

def receive_json_message(socket, topic_ref, verbosity=None):
    """
    Receives a JSON message from a ZeroMQ socket in non-blocking mode.
    
    Args:
        socket (zmq.Socket): The ZeroMQ socket.
        topic_ref (list): A mutable container to store the topic string (e.g., ['']).
        verbosity (int): Verbosity level for logging.
        
    Returns:
        dict: Parsed JSON message, or empty dict if no message or error.
    """
    try:
        # Try to receive a message in non-blocking mode
        message = socket.recv(flags=zmq.DONTWAIT).decode('utf-8')
    except zmq.Again:
        # No message available
        return {}
    except zmq.ZMQError as e:
        logging.error(f"ZeroMQ Error on receive: {e}")
        return {}

    # Get the socket type
    try:
        socket_type = socket.getsockopt(zmq.TYPE)
    except zmq.ZMQError as e:
        logging.error(f"ZeroMQ Error on getsockopt: {e}")
        socket_type = None

    # Handle SUB sockets (with topic prefix)
    json_message_str = message
    if socket_type == zmq.SUB:
        if ' ' in message:
            topic, json_message_str = message.split(' ', 1)
            topic_ref[0] = topic
        else:
            # No space found, no topic
            topic_ref[0] = ''
    else:
        topic_ref[0] = ''

    if verbosity>0:
        logging.info(f"Message: '{json_message_str}', length: {len(json_message_str)}")

    # Parse JSON
    try:
        json_message = json.loads(json_message_str)
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}")
        return {}

    return json_message

def send_json_message(socket, topic: str, json_message: dict, verbosity: int = 0) -> bool:
    try:
        # Serialize the JSON message
        message = json.dumps(json_message)

        # Create full message with topic prefix if needed
        envelope_string = f"{topic} {message}" if topic else message

        # Print debug info
        if verbosity > 0:
            print(f"[{time_string()}] Message: '{envelope_string}' (length: {len(envelope_string)})")

        # Send the message as a single string
        socket.send_string(envelope_string)

        return True

    except zmq.ZMQError as e:
        print(f"[{time_string()}] ZeroMQ Error on send: {e}")
        return False

    except Exception as e:
        print(f"[{time_string()}] General error during send: {e}")
        return False