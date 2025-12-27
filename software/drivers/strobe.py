import sys
import os

# Import from sibling module
# Note: We import from the parent package to ensure we get the same module instance
# that main.py uses, avoiding import path issues
import sys as sys_module
import os as os_module

parent_dir = os_module.path.dirname(os_module.path.dirname(os_module.path.abspath(__file__)))
if parent_dir not in sys_module.path:
    sys_module.path.insert(0, parent_dir)
from drivers import spi_handler  # noqa: E402

# Note: spi_handler.spi is a global variable set by spi_init()
# We access it as spi_handler.spi after initialization
# spi_handler handles simulation mode automatically


class PiStrobe:
    STX = 2

    def __init__(self, device_port, reply_pause_s):
        self.device_port = device_port
        self.reply_pause_s = reply_pause_s

    def read_bytes(self, bytes):
        data = []
        # Ensure spi is initialized
        if spi_handler.spi is None:
            import logging

            logger = logging.getLogger(__name__)
            logger.error("SPI not initialized! Call spi_init() before using drivers.")
            return []
        for x in range(bytes):
            data.extend(spi_handler.spi.xfer2([0]))
        return data

    def packet_read(self):
        valid = False
        type_read = 0  # Initialize type_read
        data = []
        spi_handler.spi_select_device(self.device_port)
        data_bytes = self.read_bytes(1)
        if len(data_bytes) > 0 and data_bytes[0] == self.STX:
            data_bytes.extend(self.read_bytes(2))
            if len(data_bytes) >= 3:
                size = data_bytes[1]
                type_read = data_bytes[2]
                data_bytes.extend(self.read_bytes(size - 3))
                checksum = sum(data_bytes) & 0xFF
                if checksum == 0:
                    data = data_bytes[3 : (size - 1)]
                    valid = True
        if not valid:
            data = []
        return valid, type_read, data

    def packet_write(self, type, data):
        # Ensure spi is initialized
        if spi_handler.spi is None:
            import logging

            logger = logging.getLogger(__name__)
            logger.error("SPI not initialized! Call spi_init() before using drivers.")
            return
        msg = [2, len(data) + 4, type] + data
        checksum = (-(sum(msg) & 0xFF)) & 0xFF
        msg.append(checksum)
        spi_handler.spi_select_device(self.device_port)
        spi_handler.spi.xfer2(msg)

    def packet_query(self, type, data):
        # Initialize return values in case of early exception
        valid = False
        data_read: list[int] = []
        try:
            spi_handler.spi_lock()
            self.packet_write(type, data)
            #      time.sleep( self.reply_pause_s )
            spi_handler.pi_wait_s(self.reply_pause_s)
            valid = True
            data_read = []
            type_read = 0x100
            max_read_attempts = 100  # Prevent infinite loop if PIC doesn't respond
            read_attempts = 0
            try:
                while valid and (type_read != type) and (type_read != 0) and (read_attempts < max_read_attempts):
                    valid, type_read, data_read = self.packet_read()
                    read_attempts += 1
                if read_attempts >= max_read_attempts:
                    # PIC didn't respond with expected packet type - likely communication issue
                    valid = False
                    data_read = []
            except Exception:
                valid = False
                data_read = []
            spi_handler.spi_deselect_current()
        except Exception:
            # Log error for debugging but don't raise
            # Note: We can't import logging at module level due to circular dependencies
            # in some cases, so we'll just set valid=False and let the caller handle it
            valid = False
            data_read = []
        finally:
            try:
                spi_handler.spi_release()
            except Exception:
                pass  # Ignore errors in finally block
        return valid, data_read

    def set_enable(self, enable):
        enabled = 1 if enable else 0
        valid, data = self.packet_query(1, [enabled])
        # Match old implementation: if valid is True, assume data has at least one element
        # Response should have data[0] == 0 for success
        if not valid:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"SPI communication failed for set_enable({enable}) - check hardware connection"
            )
            return False
        # Check if data has elements before accessing (safety check)
        if len(data) == 0:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Empty response from strobe hardware for set_enable({enable}) - hardware may not be responding"
            )
            return False
        success = data[0] == 0
        if not success:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Strobe hardware rejected set_enable({enable}) - response code: {data[0]}"
            )
        return success

    def set_timing(self, wait_ns, period_ns):
        wait_ns_bytes = list(wait_ns.to_bytes(4, "little", signed=False))
        period_ns_bytes = list(period_ns.to_bytes(4, "little", signed=False))
        valid, data = self.packet_query(2, wait_ns_bytes + period_ns_bytes)
        # Match old implementation behavior
        if not valid or len(data) < 9:
            # Return failure with default values
            return (False, wait_ns, period_ns)
        actual_wait_ns = int.from_bytes(data[1:5], byteorder="little", signed=False)
        actual_period_ns = int.from_bytes(data[5:9], byteorder="little", signed=False)
        # print( "data={}, wait={}, period={}, wait_bytes={}".format( data, actual_wait_ns, actual_period_ns, data[1:5] ) )
        return ((valid and (data[0] == 0)), actual_wait_ns, actual_period_ns)

    def set_hold(self, hold):
        valid, data = self.packet_query(3, [1 if hold else 0])
        # Match old implementation: if valid is True, assume data has at least one element
        # Response should have data[0] == 0 for success
        if not valid:
            return False
        # Check if data has elements before accessing (safety check)
        if len(data) == 0:
            return False
        return data[0] == 0

    def get_cam_read_time(self):
        valid, data = self.packet_query(4, [])
        if not valid or len(data) < 3:
            return (False, 0)
        cam_read_time_us = int.from_bytes(data[1:3], byteorder="little", signed=False)
        return (valid and (data[0] == 0), cam_read_time_us)

    def set_trigger_mode(self, hardware_trigger):
        """
        Set trigger mode for strobe synchronization.

        Args:
            hardware_trigger: True for hardware trigger mode (camera triggers strobe),
                             False for software trigger mode (current behavior)

        Returns:
            bool: True if successful, False otherwise
        """
        mode = 1 if hardware_trigger else 0
        valid, data = self.packet_query(5, [mode])
        return valid and (data[0] == 0)
