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
import threading
import logging
import pathlib

from .library import pack_event

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
        
        self.daqd_executable = daqd_executable

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

        def stream_output(stream, label):
            for line in iter(stream.readline, ''):
                logging.info(f"[{label}] {line.rstrip()}")

        # Spawn the daemon
        cmd = ['stdbuf', '-oL'] + cmd
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,  # Line-buffered
            text=True,
            close_fds=True
        )

        # Start threads to read both stdout and stderr
        threading.Thread(target=stream_output, args=(self.proc.stdout, "DAQD - OUT"), daemon=True).start()
        threading.Thread(target=stream_output, args=(self.proc.stderr, "DAQD - ERROR"), daemon=True).start()

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
        
    def get_daqd_pids(self):
        try:
            output = subprocess.check_output(['pgrep', '-f', self.daqd_executable], text=True)
            return [int(pid) for pid in output.strip().split()]
        except subprocess.CalledProcessError:
            return []

    def is_daqd_running(self):
        return bool(self.get_daqd_pids())

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

    def __exit__(self):
        self.stop()

    def __del__(self):
        self.stop()

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
    abcd_config: Any = None
    abcd_config_file: str = '/home/petsys/abcd/abtp2/configs/Config_example.json'

    # PETsys defaults
    client_socket_name: str = '/tmp/d.sock'
    shm_name: str = '/daqd_shm'
    daq_cards: List[str] = field(default_factory=list)
    daq_type: Optional[str] = None
    daq_card_port_bits: int = -1

    daemon: Optional[daqd_daemon] = None
    connection: Optional[Connection] = None
    acquisition_thread: Optional[threading.Thread] = None
    tp2_config_file: Any = None
    tp2_config: Any = None
    working_folder: Any = None

    # PETsys temperature
    sensor_list: List[Any] = field(default_factory=list)

    # ABCD events buffer
    events_buffer: bytearray = field(default_factory=bytearray)
    events_buffer_max_size: int = 1024

    retval: int = -1
    client_socket: int = -1
    shm_fd: int = -1
    shm_ptr: Any = None
    frame_server: Any = None

    verbosity: int = 0
    status_msg_ID: int = 0
    events_msg_ID: int = 0
    publish_temp: bool = False

    # Timing
    start_time: float = field(default_factory=lambda: time.time())
    block_start_time: float = 0.0
    stop_time: float = 0.0
    last_publication: float = field(default_factory=lambda: time.time())
    last_temp_publication: float = field(default_factory=lambda: time.time())

    def update_timestamp(self):
        self.last_publication = time.time()

    def update_temp_timestamp(self):
        self.last_temp_publication = time.time()

    def add_event(self, timestamp, qshort, qlong, baseline, channel, group_counter):
        self.events_buffer.extend(pack_event(timestamp, qshort, qlong, baseline, channel, group_counter))

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
    
