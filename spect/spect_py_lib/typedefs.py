# -----------------------------------------------------------------------------
# This file is part of ABCD.
# 2025 Nicolò Tuccori
# -----------------------------------------------------------------------------

"""
Types to interface and read PETsys TOFPET2 ASICs
Python-version of standard ABCD types
"""

from dataclasses import dataclass, field
from typing import Callable, List, Any, Optional, Dict
import time
from .timeseries import TimeSeries

class PlotType:
    ABTP2_TEMPERATURE = 0

@dataclass
class status:
    
    # ABCD defaults
    base_period: int = 100  # ms
    status_address: str = 'tcp://*:16180'
    abcd_data_address: str = 'tcp://*:16181'
    data_address: str = 'tcp://*:16181'
    commands_address: str = 'tcp://localhost:16182'

    # ZMQ context and sockets
    context: Any = None
    status_socket: Any = None
    data_socket: Any = None
    commands_socket: Any = None
    abcd_data_socket: Any = None
    spect_config: Any = None
    spect_config_file: str = '/home/petsys/abcd/spect/configs/Config_example.json'

    verbosity: int = 0
    status_msg_ID: int = 0
    data_msg_ID: int = 0

    system_start: float = field(default_factory=lambda: time.time())
    last_publication: float = field(default_factory=lambda: time.time())

    plot_type: Dict[int, int] = field(default_factory=dict)

    start_timestamp: Optional[int] = None
    enabled_channels: List[int] = field(default_factory=list)
    active_channels: Dict[int, List[int]] = field(default_factory=dict)

    channel_labels: Dict[int, str] = field(default_factory=dict)
    stream_labels_per_channel: Dict[int, List[str]] = field(default_factory=dict)
    plots_t: Dict[int, List[TimeSeries]] = field(default_factory=dict)
    
    counts_partial: Dict[int, int] = field(default_factory=dict)
    counts: Dict[int, int] = field(default_factory=dict)

    def update_timestamp(self):
        self.last_publication = time.time()

    def reset_plots(self, *channels: int):
        if channels:
            # Clear only specified channels
            for channel in channels:
                if channel in self.plots_t:
                    for stream in self.plots_t[channel]:
                        stream.reset()
        else:
            # No channels passed → clear all lists but keep keys
            for channel in self.plots_t:
                for stream in self.plots_t[channel]:
                    stream.reset()

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
    
