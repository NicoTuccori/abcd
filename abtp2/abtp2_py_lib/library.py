import zmq
import sys

def send_byte_message(socket: zmq.Socket,
                      topic: bytes,
                      buffer: bytes,
                      verbosity: int = 0) -> bool:
    """
    Sends a message through a ZeroMQ socket.

    Parameters:
    - socket:      a zmq.Socket instance (PUB)
    - topic:       the topic as bytes, or b'' for no topic
    - buffer:      payload bytes
    - verbosity:   0 = silent, >1 = debug prints

    Returns True on success, False on failure.
    """
    # Build envelope
    if topic:
        envelope = topic + b' ' + buffer
    else:
        envelope = buffer

    if verbosity > 1:
        topic_size = len(topic)
        envelope_size = len(envelope)
        print(f"Topic size: {topic_size}; Envelope size: {envelope_size}", file=sys.stderr)

    try:
        # socket.send returns number of bytes on success
        socket.send(envelope)
        return True

    except zmq.ZMQError as e:
        if verbosity > 0:
            print(f"ERROR: ZeroMQ Error on send: {e}", file=sys.stderr)
        return False
    

def receive_byte_message(socket: zmq.Socket, extract_topic: bool = True, verbosity: int = 0):
    """
    Receive a message from a ZeroMQ socket.

    Parameters:
    - socket:         a zmq.Socket (e.g. SUB)
    - extract_topic:  if True, split topic and data (default: True)
    - verbosity:      0 = silent, >0 = prints errors/info

    Returns:
    - (topic: str | None, data: bytes | None), or (None, None) if no message
    """
    try:
        # non-blocking receive
        message = socket.recv(flags=zmq.DONTWAIT)
    except zmq.Again:
        # no message available
        return None, None
    except zmq.ZMQError as e:
        if verbosity > 0:
            print(f"ERROR: ZeroMQ receive error: {e}", file=sys.stderr)
        return None, None

    if verbosity > 0:
        print(f"Received message of size: {len(message)}", file=sys.stderr)

    if extract_topic:
        try:
            topic_raw, data = message.split(b' ', 1)
            topic = topic_raw.decode('utf-8')
            if verbosity > 0:
                print(f"Extracted topic: '{topic}', Data size: {len(data)}", file=sys.stderr)
            return topic, data
        except ValueError:
            if verbosity > 0:
                print("ERROR: No topic separator found in message", file=sys.stderr)
            return None, None
    else:
        return None, message