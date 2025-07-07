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
CREATE_DIGITIZER =              state(105, "Create digitizer",              actions.create_digitizer)
# RECREATE_DIGITIZER =            state(106, "Recreate digitizer",            actions.recreate_digitizer)
CONFIGURE_DIGITIZER =           state(107, "Configure digitizer",           actions.configure_digitizer)
# ALLOCATE_MEMORY =               state(108, "Allocate memory",               actions.allocate_memory)
# RECONFIGURE_CLEAR_MEMORY =      state(109, "Reconfigure clear memory",      actions.reconfigure_clear_memory)
# RECONFIGURE_DESTROY_DIGITIZER = state(110, "Reconfigure destroy digitizer", actions.reconfigure_destroy_digitizer)

RECEIVE_COMMANDS =              state(201, "Receive commands",              actions.receive_commands)
PUBLISH_STATUS =                state(202, "Publish status",                actions.publish_status)
# START_ACQUISITION =             state(203, "Start acquisition",             actions.start_acquisition)
# STOP_ACQUISITION =              state(204, "Stop acquisition",              actions.stop_acquisition)

# ACQUISITION_RECEIVE_COMMANDS =  state(301, "Acquisition receive commands",  actions.acquisition_receive_commands)
# ADD_TO_BUFFER =                 state(303, "Read and add to events buffer", actions.add_to_buffer)
# PUBLISH_EVENTS =                state(304, "Publish events",                actions.publish_events)
# ACQUISITION_PUBLISH_STATUS =    state(305, "Acquisition publish status",    actions.acquisition_publish_status)
# STOP_PUBLISH_EVENTS =           state(306, "Publish events (stop)",         actions.stop_publish_events)
# CONTINUE_ACQUISITION =          state(307, "Continue acquisition",          actions.continue_acquisition)
# TRIGGER_RECONFIGURATION =       state(308, "Trigger reconfiguration",       actions.trigger_reconfiguration)

# RESTART_PUBLISH_EVENTS =        state(401, "Restart publish events",        actions.restart_publish_events)
# RESTART_STOP_ACQUISITION =      state(402, "Restart stop acquisition",      actions.restart_stop_acquisition)
# RESTART_CLEAR_MEMORY =          state(403, "Restart clear memory",          actions.restart_clear_memory)
# RESTART_DESTROY_DIGITIZER =     state(404, "Restart destroy digitizer",     actions.restart_destroy_digitizer)
# RESTART_CREATE_DIGITIZER =      state(405, "Restart create digitizer",      actions.restart_create_digitizer)
# RESTART_CONFIGURE_DIGITIZER =   state(406, "Restart configure digitizer",   actions.restart_configure_digitizer)
# RESTART_ALLOCATE_MEMORY =       state(407, "Restart allocate memory",       actions.restart_allocate_memory)

# CLEAR_MEMORY =                  state(801, "Clear memory",                  actions.clear_memory)
DESTROY_DIGITIZER =             state(802, "Destroy digitizer object",      actions.destroy_digitizer)
CLOSE_SOCKETS =                 state(803, "Close sockets",                 actions.close_sockets)
DESTROY_CONTEXT =               state(804, "Destroy ZeroMQ context",        actions.destroy_context)

STOP =                          state(899, "Stop",                          actions.stop)

COMMUNICATION_ERROR =           state(901, "Communication error",           actions.communication_error)
PARSE_ERROR =                   state(902, "Config parse error",            actions.parse_error)
# DIGITIZER_ERROR =               state(903, "Digitizer error",               actions.digitizer_error)
CONFIGURE_ERROR =               state(904, "Configure error",               actions.configure_error)
# ACQUISITION_ERROR =             state(905, "Acquisition error",             actions.acquisition_error)
# RESTART_CONFIGURE_ERROR =       state(906, "Restart configure error",       actions.restart_configure_error)

# List of all states
states = [
    START, CREATE_CONTEXT, CREATE_SOCKETS, BIND_SOCKETS, READ_CONFIG,
    CREATE_DIGITIZER, 
    # RECREATE_DIGITIZER, CONFIGURE_DIGITIZER, ALLOCATE_MEMORY,
    # RECONFIGURE_CLEAR_MEMORY, RECONFIGURE_DESTROY_DIGITIZER,
    # RECEIVE_COMMANDS, PUBLISH_STATUS, START_ACQUISITION, STOP_ACQUISITION,
    # ACQUISITION_RECEIVE_COMMANDS, ADD_TO_BUFFER, PUBLISH_EVENTS,
    # ACQUISITION_PUBLISH_STATUS, STOP_PUBLISH_EVENTS, CONTINUE_ACQUISITION,
    # TRIGGER_RECONFIGURATION, RESTART_PUBLISH_EVENTS, RESTART_STOP_ACQUISITION,
    # RESTART_CLEAR_MEMORY, RESTART_DESTROY_DIGITIZER, RESTART_CREATE_DIGITIZER,
    # RESTART_CONFIGURE_DIGITIZER, RESTART_ALLOCATE_MEMORY,
    # CLEAR_MEMORY, 
    DESTROY_DIGITIZER, CLOSE_SOCKETS, DESTROY_CONTEXT, STOP, COMMUNICATION_ERROR, PARSE_ERROR,
    CONFIGURE_ERROR
    # DIGITIZER_ERROR, ACQUISITION_ERROR, RESTART_CONFIGURE_ERROR
]

# Helper to lookup state by ID
STATE_MAP = {s.ID: s for s in states}
