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
    
def receive_byte_message(socket: zmq.Socket, extract_topic: bool = True, verbosity: int = 0):
    """
    Non-blocking receive of a raw byte message from a ZeroMQ socket.

    Args:
        socket (zmq.Socket): The ZeroMQ socket to read from.
        verbosity (int): >0 enables debug prints.

    Returns:
        bytes: The received message payload, or empty bytes if no message or error.
    """
    try:
        # Non-blocking receive
        message = socket.recv(flags=zmq.DONTWAIT)
    except zmq.Again:
        # No message available
        return b""
    except zmq.ZMQError as e:
        logging.error(f"ZeroMQ Error on receive: {e}")
        return b""

    if verbosity > 0:
        logging.info(f"Message length: {len(message)}")

    return message
    
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