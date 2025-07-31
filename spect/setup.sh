#!/bin/bash

# Exit on error
set -e

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv spectpy

# Activate virtual environment
echo "Activating virtual environment..."
source spectpy/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing numpy and pyzmq..."
pip install numpy pyzmq

echo "✅ Setup complete. Virtual environment ready."
