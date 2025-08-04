# -----------------------------------------------------------------------------
# This file is part of ABCD.
# 2025 Nicolò Tuccori
# -----------------------------------------------------------------------------

"""
A module for storing and analyzing time series data
"""

import numpy as np
import json
from typing import List, Union
import logging


class TimeSeries:
    def __init__(self, verbosity: int = 0):
        self.verbosity = verbosity
        self.timestamps: List[float] = []
        self.times: List[float] = []
        self.values: List[float] = []

    def add_point(self, timestamp: int, time: float, value: float):
        self.timestamps.append(timestamp)
        self.times.append(time)
        self.values.append(value)
        if self.verbosity > 1:
            print(f"Added point: time={time}, value={value}")

    def reset(self):
        self.timestamps.clear()
        self.times.clear()
        self.values.clear()
        if self.verbosity > 0:
            print("TimeSeries reset")

    def mean(self) -> float:
        return np.mean(self.values) if self.values else float("nan")

    def variance(self) -> float:
        return np.var(self.values) if self.values else float("nan")

    def stddev(self) -> float:
        return np.std(self.values) if self.values else float("nan")

    def max_value(self) -> float:
        return max(self.values) if self.values else float("nan")

    def to_dict(self) -> dict:
        return {
            "verbosity": self.verbosity,
            "data": list(zip(self.timestamps, self.times, self.values))
        }

    def from_dict(self, data: dict):
        self.verbosity = data.get("verbosity", 0)
        time_value_pairs = data.get("data", [])
        self.times, self.values = zip(*time_value_pairs) if time_value_pairs else ([], [])

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def from_json(self, json_str: str):
        self.from_dict(json.loads(json_str))

    def smooth(self, window_size: int = 5):
        if window_size < 1 or len(self.values) < window_size:
            return
        smoothed = np.convolve(self.values, np.ones(window_size)/window_size, mode='valid')
        self.values = list(smoothed)
        self.times = self.times[window_size//2: -(window_size//2)] if window_size % 2 == 1 else self.times[window_size//2: -(window_size//2) + 1]

    def isempty(self) -> bool:
        return len(self.values) == 0