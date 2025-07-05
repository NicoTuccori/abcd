from dataclasses import dataclass, field
from typing import Callable, List, Any, Optional
import time

@dataclass
class status:
    
    # ABCD defaults
    base_period: int = 100  # ms
    status_address: str = 'tcp://*:16180'
    data_address: str = 'tcp://*:16181'
    commands_address: str = 'tcp://localhost:16182'

    # ZMQ context and sockets
    context: Any = None
    status_socket: Any = None
    data_socket: Any = None
    commands_socket: Any = None

    # PETsys defaults
    client_socket_name: str = '/tmp/d.sock'
    shm_name: str = '/daqd_shm'
    daq_cards: List[str] = field(default_factory=list)
    daq_type: Optional[str] = None
    daq_card_port_bits: int = -1

    retval: int = -1
    client_socket: int = -1
    shm_fd: int = -1
    shm_ptr: Any = None
    frame_server: Any = None

    verbosity: int = 0
    status_msg_id: int = 0
    data_msg_id: int = 0

    config: Any = None

    # Timing
    start_time: float = field(default_factory=lambda: time.time())
    block_start_time: float = 0.0
    stop_time: float = 0.0
    last_publication: float = field(default_factory=lambda: time.time())
    last_baseline_check: float = field(default_factory=lambda: time.time())

    # User-defined fields
    events_buffer_max_size: int = 1024
    config_file: str = '/home/petsys/abcd/abtp2/configs/Config_example.json'
    device_number: int = 0
    daq_cards_list: List[str] = field(default_factory=list)

    def update_timestamp(self):
        self.last_publication = time.time()

# Equivalent to C++ struct state
action = Callable[[status], Any]

@dataclass
class state:
    ID: int
    description: str
    act: action

    # Equality based on ID
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, state):
            return False
        return self.ID == other.ID