import zmq, json, time
from datetime import datetime
from .library import send_byte_message, receive_byte_message
from .typedefs import status

import sys
import os

from petsys_lib import daqd

# Helper debug printer
def dbg(s, *args):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] " + s.format(*args))

#******************************************************************************/
#* Generic actions                                                            */
#******************************************************************************/

def generic_publish_events(status: status):

    if not status.waveforms_buffer:
        return
    
    total_size = sum(e.size() for e in status.waveforms_buffer)
    buf = bytearray(total_size)
    offset = 0
    
    for e in status.waveforms_buffer:
        data = e.serialize()
        buf[offset: offset+len(data)] = data
        offset += len(data)
    
    topic = f"{status.data_waveforms_topic}_v0_s{total_size}"
    
    if status.verbosity > 0:
        dbg("Sending waveforms ({} events, {} bytes)", len(status.waveforms_buffer), total_size)
    ok = send_byte_message(status.data_socket, topic.encode(), buf)
    
    if not ok:
        dbg("ERROR: publishing waveforms")
    
    status.waveforms_buffer.clear()


def generic_publish_message(status: status, topic: str, payload: dict):

    topic0 = topic
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    payload.update({
        "module": "abcd",
        "timestamp": timestamp,
        "msg_ID": status.status_msg_id
    })

    buf = json.dumps(payload, separators=(",", ":")).encode()
    topic2 = f"{topic0}_v0_s{len(buf)}"

    if status.verbosity > 0:
        dbg("Sending status '{}', {} bytes: {}", topic2, len(buf), buf)

    send_byte_message(status.status_socket, topic2.encode(), buf)

    status.status_msg_id += 1


def generic_stop_acquisition(status: status):

    dbg("Stopping acquisition")

    status.conn.stop()
    status.stop_time = time.time()

    run_time = status.stop_time - status.start_time

    if status.verbosity > 0:
        dbg("Run time: {:.2f}s", run_time)

def generic_clear_memory(status: status):

    dbg("Clearing memory buffers")

    status.counts = [0]*len(status.counts)
    status.partial_counts = [0]*len(status.partial_counts)
    status.waveforms_buffer.clear()
    status.baseline_values.clear()
    # Free blk-allocated buffers if used...

def generic_create_digitizer(status: status) -> bool:

    dbg("Creating digitizer")
    
    try:
        status.connection = daqd.Connection()
        status.connection.initializeSystem()
        return True
    
    except Exception as e:
        dbg("Error creating digitizer: {}", e)
        return False

def generic_configure_digitizer(status: status) -> bool:
    dbg("Configuring digitizer")
    return status.conn.configure()

def generic_allocate_memory(status: status) -> bool:
    dbg("Allocating memory")
    status.counts = [0]*status.n_channels
    status.partial_counts = [0]*status.n_channels
    status.baseline_values = [0.0]*status.n_channels
    status.waveforms_buffer = []
    # Optionally allocate buffers via numpy or pre-allocated bytearrays
    return True