# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# This file allows to add custom data source as sensors and display them in System Monitor themes
# There is no limitation on how much custom data source classes can be added to this file
# See CustomDataExample theme for the theme implementation part

import ctypes
import math
import mmap
import platform
import struct
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import List, Optional

from library.log import logger


# Custom data classes must be implemented in this file, inherit the CustomDataSource and implement its 2 methods
class CustomDataSource(ABC):
    @abstractmethod
    def as_numeric(self) -> float:
        # Numeric value will be used for graph and radial progress bars
        # If there is no numeric value, keep this function empty
        pass

    @abstractmethod
    def as_string(self) -> str:
        # Text value will be used for text display and radial progress bar inner text
        # Numeric value can be formatted here to be displayed as expected
        # It is also possible to return a text unrelated to the numeric value
        # If this function is empty, the numeric value will be used as string without formatting
        pass

    @abstractmethod
    def last_values(self) -> List[float]:
        # List of last numeric values will be used for plot graph
        # If you do not want to draw a line graph or if your custom data has no numeric values, keep this function empty
        pass


# Example for a custom data class that has numeric and text values
class ExampleCustomNumericData(CustomDataSource):
    # This list is used to store the last 10 values to display a line graph
    last_val = [math.nan] * 10  # By default, it is filed with math.nan values to indicate there is no data stored

    def as_numeric(self) -> float:
        # Numeric value will be used for graph and radial progress bars
        # Here a Python function from another module can be called to get data
        # Example: self.value = my_module.get_rgb_led_brightness() / audio.system_volume() ...
        self.value = 75.845

        # Store the value to the history list that will be used for line graph
        self.last_val.append(self.value)
        # Also remove the oldest value from history list
        self.last_val.pop(0)

        return self.value

    def as_string(self) -> str:
        # Text value will be used for text display and radial progress bar inner text.
        # Numeric value can be formatted here to be displayed as expected
        # It is also possible to return a text unrelated to the numeric value
        # If this function is empty, the numeric value will be used as string without formatting
        # Example here: format numeric value: add unit as a suffix, and keep 1 digit decimal precision
        return f'{self.value:>5.1f}%'
        # Important note! If your numeric value can vary in size, be sure to display it with a default size.
        # E.g. if your value can range from 0 to 9999, you need to display it with at least 4 characters every time.
        # --> return f'{self.as_numeric():>4}%'
        # Otherwise, part of the previous value can stay displayed ("ghosting") after a refresh

    def last_values(self) -> List[float]:
        # List of last numeric values will be used for plot graph
        return self.last_val


# Example for a custom data class that only has text values
class ExampleCustomTextOnlyData(CustomDataSource):
    def as_numeric(self) -> float:
        # If there is no numeric value, keep this function empty
        pass

    def as_string(self) -> str:
        # If a custom data class only has text values, it won't be possible to display graph or radial bars
        return "Python: " + platform.python_version()

    def last_values(self) -> List[float]:
        # If a custom data class only has text values, it won't be possible to display line graph
        pass


# Game FPS, read from the RivaTuner Statistics Server (RTSS) shared memory.
#
# RTSS is what MSI Afterburner uses for its on-screen display, and it publishes one entry per
# hooked application in a shared memory block. Reading it needs no overlay and costs about 1 ms.
#
# Note: the built-in STATS.GPU.FPS of this project is deliberately NOT used here. It relies on a
# LibreHardwareMonitor "Factor/FPS" sensor that does not exist on most setups, and stats.py turns
# its widgets off permanently for the whole session on the first negative reading - so booting the
# PC without a game running would hide the counter until the program is restarted.
class GameFps(CustomDataSource):
    # Shared memory published by RTSS (the "V2" block has been stable for many years)
    SHARED_MEMORY_NAME = "RTSSSharedMemoryV2"

    # Header: dwSignature, dwVersion, dwAppEntrySize, dwAppArrOffset, dwAppArrSize, and 4 more DWORDs
    HEADER_FORMAT = "<9I"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    # App entry: dwProcessID, szName[MAX_PATH], then dwFlags, dwTime0, dwTime1, dwFrames, dwFrameTime
    APP_NAME_SIZE = 260
    APP_STATS_OFFSET = 4 + APP_NAME_SIZE
    APP_STATS_FORMAT = "<5I"

    # RTSS keeps entries of applications that already exited, with their last values frozen. dwTime1
    # is a GetTickCount timestamp, so a stale entry gives itself away by its age (a live application
    # is refreshed about once per second).
    STALE_AFTER_MS = 2000

    # Displayed as "FPS 999" at most: a fixed 7-character width keeps the layout from moving
    TEXT_WIDTH = 7
    MAX_FPS = 999

    # Failures are expected (RTSS not installed, not started yet, non-Windows): log them once only
    read_error_logged = False

    def __init__(self):
        self.value = self._read_fps()

    @classmethod
    def _foreground_pid(cls) -> int:
        # When several applications are hooked at once (a game plus a launcher, for instance), the
        # one the user is actually looking at is the best answer.
        try:
            user32 = ctypes.windll.user32
            pid = ctypes.c_ulong(0)
            user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
            return pid.value
        except Exception:
            return 0

    @classmethod
    def _read_fps(cls) -> float:
        if sys.platform != "win32":
            return math.nan

        try:
            # The header has to be read first: it tells where the app array is and how big it is.
            # Mapping more than the real size of the block fails with "Access denied", so the second
            # mapping below asks for exactly the size the header announces.
            with mmap.mmap(-1, cls.HEADER_SIZE, cls.SHARED_MEMORY_NAME, access=mmap.ACCESS_READ) as shmem:
                header = struct.unpack(cls.HEADER_FORMAT, shmem.read(cls.HEADER_SIZE))
            entry_size, arr_offset, arr_size = header[2], header[3], header[4]

            if entry_size <= cls.APP_STATS_OFFSET or arr_size <= 0:
                return math.nan

            now_ms = ctypes.windll.kernel32.GetTickCount()
            foreground_pid = cls._foreground_pid()
            best_fps = math.nan

            with mmap.mmap(-1, arr_offset + entry_size * arr_size, cls.SHARED_MEMORY_NAME,
                           access=mmap.ACCESS_READ) as shmem:
                for index in range(arr_size):
                    entry = arr_offset + index * entry_size
                    pid = struct.unpack_from("<I", shmem, entry)[0]
                    if pid == 0:
                        continue

                    _, time0, time1, frames, _ = struct.unpack_from(
                        cls.APP_STATS_FORMAT, shmem, entry + cls.APP_STATS_OFFSET)
                    if time1 <= time0:
                        continue

                    # Masking keeps the subtraction right across the 32-bit GetTickCount wraparound
                    if (now_ms - time1) & 0xFFFFFFFF > cls.STALE_AFTER_MS:
                        continue

                    fps = frames * 1000.0 / (time1 - time0)
                    if pid == foreground_pid:
                        return fps
                    if math.isnan(best_fps) or fps > best_fps:
                        best_fps = fps

            return best_fps
        except Exception as e:
            if not cls.read_error_logged:
                cls.read_error_logged = True
                logger.debug("No game FPS available from RTSS shared memory: %s" % str(e))
            return math.nan

    def as_numeric(self) -> float:
        return self.value

    def as_string(self) -> str:
        if math.isnan(self.value):
            # No game running: blank the area instead of leaving the last value frozen on screen.
            # This only erases properly because the theme gives this text a fixed WIDTH/HEIGHT.
            return " " * self.TEXT_WIDTH
        return "FPS %3d" % min(int(self.value), self.MAX_FPS)

    def last_values(self) -> List[float]:
        # No line graph for this sensor
        pass


# GPU power draw, in watts.
#
# Read from LibreHardwareMonitor when the program already uses it, since the sensor is then already
# in memory and costs nothing. Falls back to nvidia-smi otherwise.
class GpuPower(CustomDataSource):
    # Sensor name varies by vendor, so try the known ones in order before giving up
    POWER_SENSOR_NAMES = ("GPU Package", "GPU Power", "GPU PPT", "GPU Core")

    LHM_MODULE_NAME = "library.sensors.sensors_librehardwaremonitor"

    # Windows CREATE_NO_WINDOW: the monitor runs under pythonw.exe, so without this flag a console
    # window would flash on screen at every reading
    CREATE_NO_WINDOW = 0x08000000

    # Displayed as "999 W" at most: fixed 5-character width
    TEXT_WIDTH = 5

    nvidia_smi_missing = False

    def __init__(self):
        self.value = self._from_librehardwaremonitor()
        if math.isnan(self.value):
            self.value = self._from_nvidia_smi()

    @classmethod
    def _from_librehardwaremonitor(cls) -> float:
        # Only reuse the module if it is already loaded: importing it has side effects, it exits the
        # whole program when not running as administrator. With HW_SENSORS other than LHM/AUTO it is
        # simply absent, and the nvidia-smi fallback takes over.
        lhm = sys.modules.get(cls.LHM_MODULE_NAME)
        if lhm is None:
            return math.nan

        try:
            hardware_type = lhm.Hardware.HardwareType
            gpu_types = (hardware_type.GpuNvidia, hardware_type.GpuAmd, hardware_type.GpuIntel)
            # Name of the GPU the rest of the program settled on, so that a machine with an
            # integrated GPU next to the discrete one reports the same card everywhere
            selected_gpu = str(lhm.Gpu.gpu_name)

            for hardware in lhm.handle.Hardware:
                if hardware.HardwareType not in gpu_types:
                    continue
                if selected_gpu and str(hardware.Name) != selected_gpu:
                    continue

                # Values are not refreshed here on purpose: the GPU stats job already calls Update()
                # on this very object every GPU.INTERVAL seconds, and calling it again from this
                # thread would mean two concurrent updates of the same hardware.
                power = {str(sensor.Name): sensor.Value for sensor in hardware.Sensors
                         if sensor.SensorType == lhm.Hardware.SensorType.Power
                         and sensor.Value is not None}
                if not power:
                    continue

                for name in cls.POWER_SENSOR_NAMES:
                    if name in power:
                        return float(power[name])
                # Unknown naming: any power sensor beats showing nothing
                return float(next(iter(power.values())))
        except Exception as e:
            logger.debug("Could not read GPU power from LibreHardwareMonitor: %s" % str(e))

        return math.nan

    @classmethod
    def _from_nvidia_smi(cls) -> float:
        if cls.nvidia_smi_missing:
            return math.nan

        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
                creationflags=cls.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            if result.returncode == 0:
                return float(result.stdout.strip().splitlines()[0])
        except FileNotFoundError:
            # No NVIDIA GPU or no driver tools installed: stop trying on every refresh
            cls.nvidia_smi_missing = True
            logger.debug("nvidia-smi not found, GPU power will not be displayed")
        except Exception as e:
            logger.debug("Could not read GPU power from nvidia-smi: %s" % str(e))

        return math.nan

    def as_numeric(self) -> float:
        return self.value

    def as_string(self) -> str:
        if math.isnan(self.value):
            return "%*s" % (self.TEXT_WIDTH, "-- W")
        return "%3d W" % round(self.value)

    def last_values(self) -> List[float]:
        # No line graph for this sensor
        pass
