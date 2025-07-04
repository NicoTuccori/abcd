#!/usr/bin/env python3
import argparse
import zmq
import json
import datetime
import logging
import threading
import queue
import time
import sched
import sys
import os
import math
import random
import struct
import json
import signal

from abtp2_py_lib.states import state
from abtp2_py_lib.actions import *
from abtp2_py_lib.typedefs import status

# Default ABCD defaults
DEFAULT_STATUS_ADDR    = 'tcp://*:16180'
DEFAULT_DATA_ADDR      = 'tcp://*:16181'
DEFAULT_COMMAND_ADDR   = 'tcp://localhost:16182'
DEFAULT_CONFIG_FILE    = '/etc/abcd/config.ini'
DEFAULT_BASE_PERIOD_MS = 100.0
DEFAULT_DEVICE_NUMBER  = 0
DEFAULT_EVENTS_BUFFER  = 1024
DEFAULT_SOCKET_NAME    = '/tmp/d.sock'
DEFAULT_DAQ_TYPE       = 'GBE'

terminate_flag = False

def signal_handler(signum, frame):
    global terminate_flag
    logging.info(f"Signal {signum} received, initiating shutdown...")
    terminate_flag = True

CMD_TO_STATE = {
    'create_context':     state.CREATE_CONTEXT,
    'create_sockets':     state.CREATE_SOCKETS,
    'create_digitizer':   state.CREATE_DIGITIZER,
    'configure_digitizer': state.CONFIGURE_DIGITIZER,
    'allocate_memory':    state.ALLOCATE_MEMORY,
    'start_acquisition':  state.START_ACQUISITION,
    'add_to_buffer':      state.ADD_TO_BUFFER,
    'publish_events':     state.PUBLISH_EVENTS,
    'stop_acquisition':   state.STOP_ACQUISITION,
    'clear_memory':       state.CLEAR_MEMORY,
    'destroy_digitizer':  state.DESTROY_DIGITIZER,
    'close_sockets':      state.CLOSE_SOCKETS,
    'destroy_context':    state.DESTROY_CONTEXT,
    'shutdown':           state.STOP
}

if __name__ == '__main__':

    # Splash screen
    print()
    print("==========================================================")
    print(" TOFPET2 software - v. 0.1                                ")
    print(" Acquisition and Broadcast for PETsys TOFPET2 ASIC series ")
    print("==========================================================")
    print()

    # Argument parsing
    parser = argparse.ArgumentParser(description="ABCD-style PETsys DAQ module in Python")
    parser.add_argument('-S', '--status-address', default=DEFAULT_STATUS_ADDR,
                        help='Status PUB socket address')
    parser.add_argument('-D', '--data-address', default=DEFAULT_DATA_ADDR,
                        help='Data PUB socket address')
    parser.add_argument('-C', '--command-address', default=DEFAULT_COMMAND_ADDR,
                        help='Commands SUB socket address')
    parser.add_argument('-f', '--config-file', default=DEFAULT_CONFIG_FILE,
                        help='Path to digitizer configuration file')
    parser.add_argument('-T', '--base-period', type=float, default=DEFAULT_BASE_PERIOD_MS,
                        help='Main loop period in milliseconds')
    parser.add_argument('-n', '--device-number', type=int, default=DEFAULT_DEVICE_NUMBER,
                        help='Device number identifier')
    parser.add_argument('-B', '--events-buffer-size', type=int, default=DEFAULT_EVENTS_BUFFER,
                        help='Maximum events buffer size')
    parser.add_argument('-s', '--socket-name', default=DEFAULT_SOCKET_NAME,
                        help='Underlying DAQ socket name, e.g. /tmp/d.sock')
    parser.add_argument('-d', '--daq-type', default=DEFAULT_DAQ_TYPE,
                        choices=['GBE','PFP_KX7'],
                        help='DAQ transport type')
    parser.add_argument('-c', '--daq-card', dest='daq_cards', action='append',
                        help='DAQ card device (can be specified multiple times)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    args = parser.parse_args()

    global_status = status()

    # If no DAQ cards provided, set default
    if not args.daq_cards:
        args.daq_cards = ['/dev/psdaq0']
    if len(args.daq_cards) > 2:
        logging.error("Maximum number of DAQ cards (2) exceeded.")
        exit(1)

    # Determine port bits
    daq_port_bits = 5 if len(args.daq_cards)==1 else 2

    # Logging
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='[%(asctime)s] %(levelname)s: %(message)s')
    logging.info(f"Device number: {args.device_number}")
    logging.info(f"Status address: {args.status_address}")
    logging.info(f"Data address: {args.data_address}")
    logging.info(f"Command address: {args.command_address}")
    logging.info(f"Config file: {args.config_file}")
    logging.info(f"Base period: {args.base_period} ms")
    logging.info(f"Events buffer size: {args.events_buffer_size}")
    logging.info(f"Socket name: {args.socket_name}")
    logging.info(f"DAQ type: {args.daq_type}")
    logging.info(f"DAQ cards: {args.daq_cards}")
    logging.info(f"DAQ port bits: {daq_port_bits}")

    # Signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    current_state = state.START
    stop_execution = False

    # Main FSM loop
    while not stop_execution:

        if terminate_flag:
            current_state = state.CLEAR_MEMORY
            terminate_flag = False
            time.sleep(1)

        if current_state == state.STOP:
            logging.info("Reached STOP state, exiting.")
            stop_execution = True

        current_state = current_state.act(global_status)

        time.sleep(1)

    logging.info("Terminated.")

    sys.exit(0)