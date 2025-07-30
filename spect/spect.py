# -----------------------------------------------------------------------------
# This file is part of ABCD.
# 2025 Nicolò Tuccori
# -----------------------------------------------------------------------------

"""
Main file to start the ABCD module to interface and read PETsys TOFPET2 ASICs
Python-version of standard ABCD main module file
"""

import argparse
import logging
import time
import sys
import signal
import os

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
DEFAULT_ABCD_DATA_ADDRESS = 'tcp://*:16181'

terminate_flag = False

def signal_handler(signum, frame):
    global verbosity

    if verbosity > 0:
        logging.info("Signal:", end=" ")

        if signum == signal.SIGINT:
            print("SIGINT")
        elif signum == signal.SIGTERM:
            print("SIGTERM")
        elif signum == signal.SIGHUP:
            print("SIGHUP")
        elif hasattr(signal, "SIGINFO") and signum == signal.SIGINFO:
            print("SIGINFO")
        else:
            print(signum)

    if signum in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]:
        terminate_event.set()
    elif hasattr(signal, "SIGINFO") and signum == signal.SIGINFO:
        logging.info(f"Running")

def print_usage(name="spect"):

    # default_address = address_bind_to_connect("", 0, defaults_abcd_data_address_sub, defaults_abcd_ip)

    print(f"Usage: {name} [options]")
    print(f"\t-h: Display this message")
    print(f"\t-A <address>: ABCD data socket address, default: {default_address}")
    print(f"\t-S <address>: Status socket address, default: {DEFAULT_SPECT_STATUS_ADDR}")
    print(f"\t-D <address>: Data socket address, default: {DEFAULT_SPECT_DATA_ADDR}")
    print(f"\t-C <address>: Commands socket address, default: {DEFAULT_SPECT_COMMAND_ADDR}")
    print(f"\t-T <period>: Set base period in milliseconds, default: {DEFAULT_BASE_PERIOD_MS}")
    print(f"\t-f <config_file>: Set config file, default: none")
    print(f"\t-v: Set verbose execution")
    print(f"\t-V: Set verbose execution with more details")

if __name__ == '__main__':

    # Check if python environment is activated
    # if 'abtp2py' not in sys.executable:
    #     print("Please activate abtp2py environment.")
    #     print("Run 'source abtp2py/bin/activate'")
    #     sys.exit(1)

    # Splash screen
    print("\n========================")
    print(" spect software - v. 0.1 ")
    print("========================\n")

    # Register signals
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    if hasattr(signal, "SIGINFO"):
        signal.signal(signal.SIGINFO, signal_handler)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-h", action="store_true")
    parser.add_argument("-A")
    parser.add_argument("-S")
    parser.add_argument("-D")
    parser.add_argument("-C")
    parser.add_argument("-T", type=int)
    parser.add_argument("-f")
    parser.add_argument("-v", action="store_true")
    parser.add_argument("-V", action="store_true")

    args, unknown = parser.parse_known_args()

    if args.h:
        print_usage(sys.argv[0])
        sys.exit(0)

    abcd_data_address = args.A or DEFAULT_SPECT_DATA_ADDR
    status_address = args.S or DEFAULT_SPECT_STATUS_ADDR
    data_address = args.D or DEFAULT_SPECT_DATA_ADDR
    commands_address = args.C or DEFAULT_SPECT_COMMAND_ADDR
    config_file = args.f or ""
    base_period = args.T if args.T is not None else DEFAULT_BASE_PERIOD_MS

    if args.v:
        verbosity = 1
    elif args.V:
        verbosity = 2

    global_status = status()
    global_status.verbosity = verbosity
    global_status.abcd_data_address = abcd_data_address
    global_status.status_address = status_address
    global_status.data_address = data_address
    global_status.commands_address = commands_address
    global_status.config_file = config_file

    if verbosity > 0:
        print(f"ABCD data socket address: {abcd_data_address}")
        print(f"Status socket address: {status_address}")
        print(f"Data socket address: {data_address}")
        print(f"Commands socket address: {commands_address}")
        print(f"Verbosity: {verbosity}")
        print(f"Base period: {base_period}")

    current_state = states["START"]
    stop_execution = False

    while not stop_execution:
        if global_status.verbosity > 0:
            logging.info(f"Current state ({current_state.ID}): {current_state.description}")

        if terminate_event.is_set():
            current_state = states["CLOSE_SOCKETS"]
            terminate_event.clear()

        if current_state == states["STOP"]:
            stop_execution = True

        current_state = current_state.act(global_status)

        sleep(base_period / 1000.0)

    logging.info("Terminated")

    sys.exit(0)