import zmq
import time
import struct
import random
import logging

# Struct and packing function
EVENT_STRUCT = struct.Struct('<QHHHBB')

def pack_event(timestamp: int, qshort: int, qlong: int, baseline: int, channel: int, group_counter: int) -> bytes:
    return EVENT_STRUCT.pack(timestamp, qshort, qlong, baseline, channel, group_counter)

def send_byte_message(socket: zmq.Socket,
                      topic: bytes,
                      buffer_bytes: bytes,
                      verbosity: int = 0) -> bool:
    if topic:
        topic_with_space = topic + b" "
    else:
        topic_with_space = b""

    try:
        payload = bytes(buffer_bytes)
    except Exception as e:
        logging.error(f"Error converting payload to bytes: {e}")
        return False

    frame = topic_with_space + payload
    envelope_size = len(frame)

    if verbosity > 0:
        logging.info(f"Sending message of size: {envelope_size}")

    try:
        socket.send(frame, flags=0)
    except zmq.ZMQError as e:
        logging.error(f"ZeroMQ send error: {e}")
        return False

    return True

def encode_temp_sensor(kind: int, sensorID: int, moduleID: int, slaveID: int, portID: int) -> int:
    encoded = 0
    encoded |= (kind & 0x01)           # bit 0
    encoded |= (sensorID & 0x07) << 3  # bits 3-5
    encoded |= (moduleID & 0x0F) << 6  # bits 6-9
    encoded |= (slaveID & 0x07) << 10  # bits 10-12
    encoded |= (portID & 0x07) << 13   # bits 13-15
    return encoded

# Dummy data sender
def send_dummy_temperature_data(pub_address='tcp://127.0.0.1:16181', topic="data_abcd_events", n_events=1000, delay=5.0, verbosity=1):
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(pub_address)
    time.sleep(0.2)  # Let bind settle

    for i in range(n_events):
        
        event_buffer = bytearray()
        for ch in range(0,7):
            timestamp = int(time.time())
            qshort = random.randint(20, 80)*100  # e.g. fake temperature ADC
            qlong = 0
            baseline = encode_temp_sensor(kind=1, sensorID=0, moduleID=0, slaveID=0, portID=ch)
            channel = 0
            group_counter = i % 256

            event_bytes = pack_event(timestamp, qshort, qlong, baseline, channel, group_counter)
            event_buffer.extend(event_bytes)

        success = send_byte_message(socket, topic.encode('utf-8'), event_buffer, verbosity=verbosity)

        if success and verbosity > 0:
            print(f"Sent dummy temp event {i}: Qshort={qshort}, Qlong={qlong}")

        time.sleep(delay)

    socket.close()
    context.term()

# Run it directly for testing
if __name__ == "__main__":
    send_dummy_temperature_data()
