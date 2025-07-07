# -----------------------------------------------------------------------------
# This file is part of ABCD.
# 2025 Nicolò Tuccori
# -----------------------------------------------------------------------------

"""
Types to interface and read PETsys TOFPET2 ASICs
Python-version of standard ABCD types
"""

from dataclasses import dataclass, field
from typing import Callable, List, Any, Optional
import time
from .petsys_lib.daqd import Connection
import subprocess
import time
import os
import socket

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

    daemon: Optional[daqd_daemon] = None
    connection: Optional[Connection] = None

    retval: int = -1
    client_socket: int = -1
    shm_fd: int = -1
    shm_ptr: Any = None
    frame_server: Any = None

    verbosity: int = 0
    status_msg_ID: int = 0
    data_msg_ID: int = 0

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
    

# manager of the daqd daemon
class daqd_daemon:
    def __init__(self,
                 daqd_executable: str    = "./daqd",
                 daq_type: str           = "GBE",
                 socket_path: str        = "/tmp/d.sock",
                 shm_name: str           = "/daqd_shm",
                 debug_level: int        = 1,
                 card_paths: list[str]   = ["/dev/psdaq0"],
                 startup_timeout: float  = 5.0):
        """
        Launches the C++ daqd daemon and waits for it to listen on the UNIX socket.
        """
        # Build the command line
        cmd = [
            daqd_executable,
            "--daq-type",   daq_type,
            "--socket-name", socket_path,
            "--debug-level", str(debug_level),
        ]
        # allow multiple --card entries
        for card in card_paths:
            cmd += ["--card", card]

        # Remove any stale socket
        try:
            os.unlink(socket_path)
        except FileNotFoundError:
            pass

        # Spawn the daemon
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True
        )

        # Wait for the socket to appear & be connectable
        deadline = time.time() + startup_timeout
        while time.time() < deadline:
            if os.path.exists(socket_path):
                try:
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.settimeout(0.2)
                    sock.connect(socket_path)
                    sock.close()
                    break
                except (ConnectionRefusedError, socket.timeout):
                    pass
            time.sleep(0.1)
        else:
            # timed out
            self.proc.terminate()
            raise RuntimeError(f"daqd did not start listening on {socket_path}")

    def stop(self):
        """
        Ask the daemon to exit (via SIGINT) and wait for it to die.
        """
        if self.proc.poll() is None:
            self.proc.send_signal(subprocess.signal.SIGINT)
            try:
                self.proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()
