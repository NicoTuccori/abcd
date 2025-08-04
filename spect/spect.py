# -----------------------------------------------------------------------------
# This file is part of ABCD.
# 2025 Nicolò Tuccori
# -----------------------------------------------------------------------------

"""
Main file to start the SPECT module to plot ABCD data over time
Python-version of standard ABCD main module file
"""

import argparse
import logging
import time
import sys
import signal

import spect_py_lib.states as states
from spect_py_lib.typedefs import status

# Default SPECT
DEFAULT_SPECT_STATUS_ADDR    = 'tcp://*:16187'
DEFAULT_SPECT_DATA_ADDR      = 'tcp://*:16188'
DEFAULT_SPECT_COMMAND_ADDR   =  "tcp://*:16189"
DEFAULT_CONFIG_FILE    = '/home/petsys/abcd/spect/configs/Config_example.json'
DEFAULT_BASE_PERIOD_MS = 100.0
DEFAULT_EVENTS_BUFFER  = 1024

# Default ABCD
DEFAULT_ABCD_DATA_ADDRESS_SUB = "tcp://127.0.0.1:16181"

terminate_flag = False

def signal_handler(signum, frame):
    global terminate_flag
    logging.info(f"Signal {signum} received, initiating shutdown...")
    terminate_flag = True

if __name__ == '__main__':

    # Check if python environment is activated
    if 'spectpy' not in sys.executable:
        print("Please activate spectpy environment.")
        print("Run 'source spectpy/bin/activate'")
        sys.exit(1)

    # Splash screen
    print("\n========================")
    print(" spect software - v. 0.1 ")
    print("========================\n")

    parser = argparse.ArgumentParser(description="ABCD SPECT module -> plot ABCD data over time")
    parser.add_argument('-A', '--abcd-data-address', dest='abcd_data_address', default=DEFAULT_ABCD_DATA_ADDRESS_SUB,
                        help='ABCD data socket address')
    parser.add_argument('-S', '--status-address', dest='status_address', default=DEFAULT_SPECT_STATUS_ADDR,
                        help='Status PUB socket address')
    parser.add_argument('-D', '--data-address', dest='data_address', default=DEFAULT_SPECT_DATA_ADDR,
                        help='Data PUB socket address')
    parser.add_argument('-C', '--command-address', dest='command_address', default=DEFAULT_SPECT_COMMAND_ADDR,
                        help='Commands SUB socket address')
    parser.add_argument('-f', '--config-file', dest='spect_config_file', default=DEFAULT_CONFIG_FILE,
                        help='Path to spect configuration file')
    parser.add_argument('-T', '--base-period', dest='base_period', default=DEFAULT_BASE_PERIOD_MS,
                        help='Base period in milliseconds')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    args = parser.parse_args()

    global_status = status()

    global_status.verbosity = args.verbose
    global_status.abcd_data_address = args.abcd_data_address
    global_status.status_address = args.status_address
    global_status.data_address = args.data_address
    global_status.commands_address = args.command_address
    global_status.spect_config_file = args.spect_config_file

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s'
    )

    if global_status.verbosity > 0:
        logging.info(f"ABCD data socket address: {global_status.abcd_data_address}")
        logging.info(f"Status socket address: {global_status.status_address}")
        logging.info(f"Data socket address: {global_status.data_address}")
        logging.info(f"Commands socket address: {global_status.commands_address}")
        logging.info(f"Verbosity: {global_status.verbosity}")
        logging.info(f"Base period: {global_status.base_period}")

    # Signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    current_state = states.START
    stop_execution = False

    logging.info("Let's go!")

    while not stop_execution:

        if terminate_flag:
                
            current_state = states.CLOSE_SOCKETS
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