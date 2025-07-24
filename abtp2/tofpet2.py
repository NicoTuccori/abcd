# -----------------------------------------------------------------------------
# This file is part of ABCD.
# 2025 Nicolò Tuccori
# -----------------------------------------------------------------------------

"""
Main file to start the ABCD module to interface and read PETsys TOFPET2 ASICs
Python-version of standard ABCD main module file
"""

#!~/abcd/abtp2/abtp2py/bin python3

import argparse
import logging
import time
import sys
import signal
import os

import abtp2_py_lib.states as states
from abtp2_py_lib.typedefs import status

# Default ABCD defaults
DEFAULT_STATUS_ADDR    = 'tcp://*:16180'
DEFAULT_DATA_ADDR      = 'tcp://*:16181'
DEFAULT_COMMAND_ADDR   = 'tcp://localhost:16182'
DEFAULT_CONFIG_FILE    = '/home/petsys/abcd/abtp2/configs/Config_example.json'
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

if __name__ == '__main__':

    # Check if python environment is activated
    if 'abtp2py' not in sys.executable:
        print("Please activate abtp2py environment.")
        print("Run 'source abtp2py/bin/activate'")
        sys.exit(1)

    # Splash screen
    print()
    print("==========================================================")
    print(" TOFPET2 software - v. 0.1                                ")
    print(" Acquisition and Broadcast for PETsys TOFPET2 ASIC series ")
    print("==========================================================")
    print()

    # Argument parsing
    parser = argparse.ArgumentParser(description="ABCD-style PETsys DAQ module in Python")
    parser.add_argument('-S', '--status-address', dest='status_address', default=DEFAULT_STATUS_ADDR,
                        help='Status PUB socket address')
    parser.add_argument('-D', '--data-address', dest='data_address', default=DEFAULT_DATA_ADDR,
                        help='Data PUB socket address')
    parser.add_argument('-C', '--command-address', dest='command_address', default=DEFAULT_COMMAND_ADDR,
                        help='Commands SUB socket address')
    parser.add_argument('-f', '--config-file', dest='abcd_config_file', default=DEFAULT_CONFIG_FILE,
                        help='Path to digitizer configuration file')
    parser.add_argument('-s', '--socket-name', dest='socket_name', default=DEFAULT_SOCKET_NAME,
                        help='Underlying DAQ socket name, e.g. /tmp/d.sock')
    parser.add_argument('-d', '--daq-type', dest='daq_type', default=DEFAULT_DAQ_TYPE,
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
    global_status.daq_cards = args.daq_cards

    # Determine port bits
    daq_port_bits = 5 if len(args.daq_cards)==1 else 2
    global_status.daq_card_port_bits = daq_port_bits

    global_status.verbosity = args.verbose
    global_status.status_address = args.status_address
    global_status.data_address = args.data_address
    global_status.commands_address = args.command_address
    if not os.path.exists(args.abcd_config_file):
        logging.error(f"Config file does not exists: {args.abcd_config_file}")
        exit(1)
    global_status.abcd_config_file = args.abcd_config_file
    global_status.working_folder = os.path.dirname(args.abcd_config_file)
    if global_status.working_folder == None:
        logging.error(f"Please define the config file in an existing working folder. Got {global_status.working_folder}")
        exit(1)
    global_status.daq_type = args.daq_type
    global_status.client_socket_name = args.socket_name

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s'
    )
    
    if global_status.verbosity:
        logging.info(f"Status address: {global_status.status_address}")
        logging.info(f"Data address: {global_status.data_address}")
        logging.info(f"Command address: {global_status.commands_address}")
        logging.info(f"Config file: {global_status.abcd_config_file}")
        logging.info(f"Socket name: {global_status.client_socket_name}")
        logging.info(f"DAQ type: {global_status.daq_type}")
        logging.info(f"DAQ cards: {global_status.daq_cards}")
        logging.info(f"DAQ port bits: {daq_port_bits}")

    # Signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    current_state = states.START
    stop_execution = False

    logging.info("Let's go!")

    while not stop_execution:

        if terminate_flag:

            if current_state == states.ACQUISITION_RECEIVE_COMMANDS or current_state == states.POLL_DIGITIZER:
                current_state = states.STOP_ACQUISITION
                current_state = current_state.act(global_status)
                if global_status.verbosity > 0:
                    logging.info("Acquisition was running. Stopping it.")
                time.sleep(1)
                
            current_state = states.DESTROY_DIGITIZER
            terminate_flag = False
            time.sleep(1)

        if current_state == states.STOP:
            if global_status.verbosity > 0:
                logging.info("Stop\t\t\t-> EXIT")
            stop_execution = True

        current_state = current_state.act(global_status)

        time.sleep(1)

    logging.info("Terminated")

    sys.exit(0)