# File: states.py
from enum import Enum, auto
from typing import List
from .typedefs import state

# Define basic states
class states(Enum):
    START = auto()
    CREATE_CONTEXT = auto()
    CREATE_SOCKETS = auto()
    BIND_SOCKETS = auto()
    READ_CONFIG = auto()
    CREATE_DIGITIZER = auto()
    RECREATE_DIGITIZER = auto()
    CONFIGURE_DIGITIZER = auto()
    ALLOCATE_MEMORY = auto()
    RECONFIGURE_CLEAR_MEMORY = auto()
    RECONFIGURE_DESTROY_DIGITIZER = auto()
    RECEIVE_COMMANDS = auto()
    PUBLISH_STATUS = auto()
    START_ACQUISITION = auto()
    STOP_ACQUISITION = auto()
    ACQUISITION_RECEIVE_COMMANDS = auto()
    ADD_TO_BUFFER = auto()
    PUBLISH_EVENTS = auto()
    ACQUISITION_PUBLISH_STATUS = auto()
    STOP_PUBLISH_EVENTS = auto()
    CONTINUE_ACQUISITION = auto()
    TRIGGER_RECONFIGURATION = auto()
    RESTART_PUBLISH_EVENTS = auto()
    RESTART_STOP_ACQUISITION = auto()
    RESTART_CLEAR_MEMORY = auto()
    RESTART_DESTROY_DIGITIZER = auto()
    RESTART_CREATE_DIGITIZER = auto()
    RESTART_CONFIGURE_DIGITIZER = auto()
    RESTART_ALLOCATE_MEMORY = auto()
    CLEAR_MEMORY = auto()
    DESTROY_DIGITIZER = auto()
    CLOSE_SOCKETS = auto()
    DESTROY_CONTEXT = auto()
    STOP = auto()
    COMMUNICATION_ERROR = auto()
    PARSE_ERROR = auto()
    DIGITIZER_ERROR = auto()
    CONFIGURE_ERROR = auto()
    ACQUISITION_ERROR = auto()
    RESTART_CONFIGURE_ERROR = auto()

# List of all state entries mirroring C++ definitions
STATE_TABLE: List[state] = [
    state(100, "Start",     lambda s: None),
    state(101, "Create ZeroMQ context",    lambda s: None),
    state(102, "Create sockets",            lambda s: None),
    state(103, "Bind sockets",              lambda s: None),
    state(104, "Read configuration",        lambda s: None),
    state(105, "Create digitizer",          lambda s: None),
    state(106, "Recreate digitizer",        lambda s: None),
    state(107, "Configure digitizer",       lambda s: None),
    state(108, "Allocate memory",           lambda s: None),
    state(109, "Reconfigure clear memory",  lambda s: None),
    state(110, "Reconfigure destroy digitizer", lambda s: None),
    state(201, "Receive commands",          lambda s: None),
    state(202, "Publish status",            lambda s: None),
    state(203, "Start acquisition",         lambda s: None),
    state(204, "Stop acquisition",          lambda s: None),
    state(301, "Acquisition receive commands", lambda s: None),
    state(303, "Read and add to events buffer", lambda s: None),
    state(304, "Publish events",            lambda s: None),
    state(305, "Acquisition publish status",lambda s: None),
    state(306, "Publish events (stop)",     lambda s: None),
    state(307, "Continue acquisition",      lambda s: None),
    state(308, "Trigger reconfiguration",   lambda s: None),
    state(401, "Restart publish events",    lambda s: None),
    state(402, "Restart stop acquisition",  lambda s: None),
    state(403, "Restart clear memory",      lambda s: None),
    state(404, "Restart destroy digitizer", lambda s: None),
    state(405, "Restart create digitizer",  lambda s: None),
    state(406, "Restart configure digitizer", lambda s: None),
    state(407, "Restart allocate memory",   lambda s: None),
    state(801, "Destroy digitizer object", lambda s: None),
    state(802, "Destroy digitizer object", lambda s: None),
    state(803, "Close sockets",            lambda s: None),
    state(804, "Destroy ZeroMQ context",   lambda s: None),
    state(899, "Stop",                     lambda s: None),
    state(901, "Communication error",      lambda s: None),
    state(902, "Config parse error",       lambda s: None),
    state(903, "Digitizer error",         lambda s: None),
    state(903, "Configure error",         lambda s: None),
    state(904, "Acquisition error",        lambda s: None),
    state(905, "Restart configure error",  lambda s: None),
]

# Helper to lookup state by State enum
STATE_MAP = {state: entry for state, entry in zip(states, STATE_TABLE)}