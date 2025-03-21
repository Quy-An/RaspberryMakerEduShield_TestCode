"""Driver for L9110 motor controller over I2C using smbus2."""

from smbus2 import SMBus


class L9110:
    """A class to control the L9110 motor driver via I2C.

    Attributes:
        address (int): I2C address of the L9110 device (default: 0x40).
        bus_number (int): I2C bus number (default: 1).
    """

    # Constants for modes and motors
    MODE_RC = 0  # Servo mode
    S1 = 1       # Servo 1
    S2 = 2       # Servo 2
    MODE_DC = 1  # DC motor mode
    MA = 0       # Motor A
    MB = 1       # Motor B
    CW = 0       # Clockwise
    CCW = 1      # Counterclockwise
    MODE_SET_ADDR = 2  # Mode to set new address

    def __init__(self, address=0x40, bus_number=1):
        """Initialize the L9110 driver.

        Args:
            address (int): I2C address of the device (default: 0x40).
            bus_number (int): I2C bus number (default: 1).
        """
        self.address = address
        self.bus = SMBus(bus_number)

        # Default ranges for servo control
        self.min_degree = 0
        self.max_degree = 180
        self.min_pulse = 500
        self.max_pulse = 2500

    def __enter__(self):
        """Support context manager: return self when entering 'with' block."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the I2C bus when exiting 'with' block."""
        self.bus.close()

    def __del__(self):
        """Close the I2C bus when the object is destroyed."""
        self.bus.close()

    def _map_range(self, x, in_min, in_max, out_min, out_max):
        """Map a value from one range to another.

        Args:
            x (float): Input value.
            in_min (float): Minimum of input range.
            in_max (float): Maximum of input range.
            out_min (float): Minimum of output range.
            out_max (float): Maximum of output range.

        Returns:
            int: Mapped value.
        """
        return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

    def set_range_degree(self, min_degree, max_degree):
        """Set the degree range for servo control.

        Args:
            min_degree (int): Minimum degree (0-359).
            max_degree (int): Maximum degree (1-360).

        Returns:
            bool: True if successful, False if range is invalid.
        """
        if not (0 <= min_degree < max_degree <= 360):
            print("Error: Degree range invalid. Ensure: 0 <= min < max <= 360")
            return False
        self.min_degree = min_degree
        self.max_degree = max_degree
        return True

    def set_range_pulse(self, min_pulse, max_pulse):
        """Set the pulse range for servo control.

        Args:
            min_pulse (int): Minimum pulse width (0-2814).
            max_pulse (int): Maximum pulse width (1-2815).

        Returns:
            bool: True if successful, False if range is invalid.
        """
        if not (0 <= min_pulse < max_pulse <= 2815):
            print("Error: Pulse range invalid. Ensure: 0 <= min < max <= 2815")
            return False
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        return True

    def _send_data(self, data):
        """Send data to the L9110 device over I2C.

        Args:
            data (list): Data to send, where data[0] is the mode/register.

        Returns:
            bool: True if successful, False if an I2C error occurs.
        """
        try:
            self.bus.write_i2c_block_data(self.address, data[0], data[1:])
            return True
        except IOError as e:
            print(f"I2C Error: {e}")
            return False

    def control_servo(self, servo_id, degree):
        """Control a servo motor.

        Args:
            servo_id (int): Servo ID (S1 or S2).
            degree (float): Desired angle in degrees.

        Returns:
            bool: True if successful, False if degree is out of range or I2C fails.
        """
        if not (self.min_degree <= degree <= self.max_degree):
            print(f"Error: Degree {degree} out of range ({self.min_degree}-{self.max_degree})")
            return False

        data = [self.MODE_RC, servo_id, 0, 0, 0]
        pulse = self._map_range(degree, self.min_degree, self.max_degree, self.min_pulse, self.max_pulse)
        data[2] = pulse >> 8
        data[3] = pulse & 0xFF
        data[4] = sum(data) & 0xFF  # Checksum

        return self._send_data(data)

    def control_motor(self, motor_id, percent, direction):
        """Control a DC motor.

        Args:
            motor_id (int): Motor ID (MA or MB).
            percent (float): Speed percentage (0-100).
            direction (int): Direction (CW or CCW).

        Returns:
            bool: True if successful, False if parameters are invalid or I2C fails.
        """
        if not (0 <= percent <= 100):
            print(f"Error: Percent {percent} out of range (0-100)")
            return False
        if direction not in (self.CW, self.CCW):
            print(f"Error: Direction {direction} invalid (use {self.CW} or {self.CCW})")
            return False

        data = [self.MODE_DC, motor_id, 0, 0, 0]
        data[2] = self._map_range(percent, 0, 100, 0, 255)
        data[3] = direction
        data[4] = sum(data) & 0xFF  # Checksum

        return self._send_data(data)

    def set_address(self, new_address):
        """Change the I2C address of the device.

        Args:
            new_address (int): New I2C address (0x40 to 0x44).

        Returns:
            bool: True if successful, False if address is invalid or I2C fails.
        """
        if not (0x40 <= new_address <= 0x44):
            print("Error: New address must be between 0x40 and 0x44")
            return False

        data = [self.MODE_SET_ADDR, 0, 0, 0, new_address + self.MODE_SET_ADDR]
        if self._send_data(data):
            self.address = new_address
            print(f"Set address successful. New address: {hex(new_address)}")
            return True
        return False