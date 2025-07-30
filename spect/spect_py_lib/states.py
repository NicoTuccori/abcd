# -----------------------------------------------------------------------------
# This file is part of ABCD.
# 2025 Nicolò Tuccori
# -----------------------------------------------------------------------------

"""
States to interface and read PETsys TOFPET2 ASICs
Python-version of standard ABCD states
"""

from .typedefs import state
from . import actions

# Define states
START =                         state(100, "Start",                         actions.start)
CREATE_CONTEXT =                state(101, "Create ZeroMQ context",         actions.create_context)
CREATE_SOCKETS =                state(102, "Create sockets",                actions.create_sockets)
BIND_SOCKETS =                  state(103, "Bind sockets",                  actions.bind_sockets)
READ_CONFIG =                   state(104, "Read configuration",            actions.read_config)

RECEIVE_COMMANDS =              state(201, "Receive commands",              actions.receive_commands)
PUBLISH_STATUS =                state(202, "Publish status",                actions.publish_status)
READ_SOCKET =                   state(203, "Read socket",                   actions.read_socket)
PUBLISH_DATA =                  state(204, "Publish data",                  actions.publish_data)

CLOSE_SOCKETS =                 state(803, "Close sockets",                 actions.close_sockets)
DESTROY_CONTEXT =               state(804, "Destroy ZeroMQ context",        actions.destroy_context)
STOP =                          state(899, "Stop",                          actions.stop)

COMMUNICATION_ERROR =           state(901, "Communication error",           actions.communication_error)

# List of all states
states = [
    START, CREATE_CONTEXT, CREATE_SOCKETS, BIND_SOCKETS, READ_CONFIG,
    RECEIVE_COMMANDS, PUBLISH_STATUS, 
    CLOSE_SOCKETS, DESTROY_CONTEXT, STOP, COMMUNICATION_ERROR
]

# Helper to lookup state by ID
STATE_MAP = {s.ID: s for s in states}
