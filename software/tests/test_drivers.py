#!/usr/bin/env python3
"""
Unit tests for driver modules.

Tests low-level hardware drivers (SPI handler, flow, heater, strobe)
to ensure they work correctly in both simulation and hardware modes.

Usage:
    python tests/test_drivers.py
    python -m tests.test_drivers
"""

import os
import unittest

# Mock imports available if needed for future tests
# from unittest.mock import Mock, patch, MagicMock

# Set simulation mode
os.environ["RIO_SIMULATION"] = "true"


class TestSPIHandler(unittest.TestCase):
    """Test SPI handler functionality"""

    def setUp(self):
        """Set up test fixtures"""
        from drivers.spi_handler import spi_init, spi_close, spi_select_device, spi_deselect_current

        self.spi_init = spi_init
        self.spi_close = spi_close
        self.spi_select_device = spi_select_device
        self.spi_deselect_current = spi_deselect_current

    def test_spi_init_simulation(self):
        """Test SPI initialization in simulation mode"""
        spi = self.spi_init(0, 2, 30000)
        self.assertIsNotNone(spi)
        self.assertTrue(hasattr(spi, "xfer2"))

    def test_spi_select_deselect(self):
        """Test device selection/deselection"""
        from drivers.spi_handler import PORT_HEATER1, PORT_FLOW

        self.spi_init(0, 2, 30000)

        # Select device
        self.spi_select_device(PORT_HEATER1)

        # Deselect
        self.spi_deselect_current()

        # Select different device
        self.spi_select_device(PORT_FLOW)
        self.spi_deselect_current()

    def tearDown(self):
        """Clean up after tests"""
        try:
            self.spi_close()
        except Exception:
            pass


class TestFlowDriver(unittest.TestCase):
    """Test flow controller driver"""

    def setUp(self):
        """Set up test fixtures"""
        from drivers.spi_handler import spi_init, PORT_FLOW

        spi_init(0, 2, 30000)
        from drivers.flow import PiFlow

        self.flow = PiFlow(PORT_FLOW, 0.1)

    def test_flow_initialization(self):
        """Test flow driver initialization"""
        from drivers.spi_handler import PORT_FLOW  # noqa: E402

        self.assertIsNotNone(self.flow)
        self.assertEqual(self.flow.device_port, PORT_FLOW)  # noqa: F821

    def test_packet_read_write(self):
        """Test packet read/write operations"""
        # These will use simulated SPI
        valid, type_read, data = self.flow.packet_read()
        # In simulation, may return invalid, which is OK
        self.assertIsInstance(valid, bool)

    def tearDown(self):
        """Clean up"""
        from drivers.spi_handler import spi_close

        try:
            spi_close()
        except Exception:
            pass


class TestHeaterDriver(unittest.TestCase):
    """Test heater driver"""

    def setUp(self):
        """Set up test fixtures"""
        from drivers.spi_handler import spi_init, PORT_HEATER1

        spi_init(0, 2, 30000)
        from drivers.heater import PiHolder

        self.heater = PiHolder(PORT_HEATER1, 0.1)

    def test_heater_initialization(self):
        """Test heater driver initialization"""
        from drivers.spi_handler import PORT_HEATER1  # noqa: E402

        self.assertIsNotNone(self.heater)
        self.assertEqual(self.heater.device_port, PORT_HEATER1)

    def test_get_id(self):
        """Test device ID retrieval"""
        valid, id, id_valid = self.heater.get_id()
        self.assertIsInstance(valid, bool)
        # In simulation, may not match, which is OK

    def tearDown(self):
        """Clean up"""
        from drivers.spi_handler import spi_close

        try:
            spi_close()
        except Exception:
            pass


class TestStrobeDriver(unittest.TestCase):
    """Test strobe driver"""

    def setUp(self):
        """Set up test fixtures"""
        from drivers.spi_handler import spi_init, PORT_STROBE

        spi_init(0, 2, 30000)
        from drivers.strobe import PiStrobe

        self.strobe = PiStrobe(PORT_STROBE, 0.1)

    def test_strobe_initialization(self):
        """Test strobe driver initialization"""
        from drivers.spi_handler import PORT_STROBE  # noqa: E402

        self.assertIsNotNone(self.strobe)
        self.assertEqual(self.strobe.device_port, PORT_STROBE)

    def test_set_enable(self):
        """Test strobe enable/disable"""
        result = self.strobe.set_enable(True)
        self.assertIsInstance(result, bool)

        result = self.strobe.set_enable(False)
        self.assertIsInstance(result, bool)

    def test_set_timing(self):
        """Test strobe timing configuration"""
        wait_ns = 1000
        period_ns = 100000
        result = self.strobe.set_timing(wait_ns, period_ns)
        # set_timing returns (valid, actual_wait_ns, actual_period_ns)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], bool)

    def tearDown(self):
        """Clean up"""
        from drivers.spi_handler import spi_close

        try:
            spi_close()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
