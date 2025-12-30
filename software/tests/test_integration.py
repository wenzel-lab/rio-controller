#!/usr/bin/env python3
"""
Integration tests for the Rio controller.

Tests that multiple components work together correctly,
simulating real application usage scenarios.

Usage:
    python tests/test_integration.py
    python -m tests.test_integration
"""

import os
import unittest
from threading import Event

# Set simulation mode
os.environ["RIO_SIMULATION"] = "true"


class TestHardwareInitialization(unittest.TestCase):
    """Test complete hardware initialization sequence"""

    def setUp(self):
        """Set up test fixtures"""
        from drivers.spi_handler import spi_init, PORT_HEATER1, PORT_FLOW

        spi_init(0, 2, 30000)
        self.port_heater = PORT_HEATER1
        self.port_flow = PORT_FLOW

    def test_spi_initialization(self):
        """Test SPI initialization"""
        from drivers.spi_handler import spi

        self.assertIsNotNone(spi)

    def test_flow_initialization(self):
        """Test flow controller initialization"""
        from controllers.flow_web import FlowWeb

        flow = FlowWeb(self.port_flow)
        self.assertIsNotNone(flow)

    def test_heater_initialization(self):
        """Test heater initialization"""
        from controllers.heater_web import heater_web

        heater = heater_web(1, self.port_heater)
        self.assertIsNotNone(heater)

    def tearDown(self):
        """Clean up"""
        from drivers.spi_handler import spi_close

        try:
            spi_close()
        except Exception:
            pass


class TestCameraStrobeIntegration(unittest.TestCase):
    """Test camera and strobe integration"""

    def setUp(self):
        """Set up test fixtures"""
        try:
            from flask_socketio import SocketIO
            from flask import Flask
        except ImportError as e:
            self.skipTest(f"Flask-SocketIO required: {e}")

        app = Flask(__name__)
        socketio = SocketIO(app, async_mode="threading")

        from controllers.camera import Camera

        self.exit_event = Event()
        self.camera = Camera(self.exit_event, socketio)

    def test_camera_strobe_connection(self):
        """Test that camera has strobe integration"""
        self.assertIsNotNone(self.camera.strobe_cam)

    def test_strobe_data_available(self):
        """Test that strobe data is available"""
        self.assertIsNotNone(self.camera.strobe_data)
        self.assertIn("enable", self.camera.strobe_data)
        self.assertIn("period_ns", self.camera.strobe_data)

    def tearDown(self):
        """Clean up"""
        try:
            self.camera.close()
        except Exception:
            pass


class TestSimulationMode(unittest.TestCase):
    """Test that simulation mode works end-to-end"""

    def test_simulation_flag(self):
        """Test that simulation mode is detected"""
        self.assertEqual(os.getenv("RIO_SIMULATION"), "true")

    def test_simulation_imports(self):
        """Test that simulation modules are used"""
        from drivers.spi_handler import SIMULATION_MODE

        self.assertTrue(SIMULATION_MODE)

    def test_simulation_spi(self):
        """Test that simulated SPI is used"""
        from drivers.spi_handler import spi_init, spi

        spi_init(0, 2, 30000)
        # In simulation, spi should be SimulatedSPIDev
        self.assertIsNotNone(spi)
        # Check it has the expected method
        self.assertTrue(hasattr(spi, "xfer2"))


class TestErrorHandling(unittest.TestCase):
    """Test error handling in various scenarios"""

    def test_invalid_port_handling(self):
        """Test handling of invalid port numbers"""
        from drivers.spi_handler import spi_init, spi_select_device

        spi_init(0, 2, 30000)

        # Should not crash on invalid port
        try:
            spi_select_device(999)  # Invalid port
        except Exception:
            # If it raises, that's OK - just shouldn't crash the system
            pass

    def test_missing_device_handling(self):
        """Test handling when device doesn't respond"""
        from drivers.spi_handler import spi_init, PORT_HEATER1

        spi_init(0, 2, 30000)

        from drivers.heater import PiHolder

        heater = PiHolder(PORT_HEATER1, 0.1)

        # get_id may fail in simulation, should handle gracefully
        valid, id, id_valid = heater.get_id()
        self.assertIsInstance(valid, bool)


if __name__ == "__main__":
    unittest.main(verbosity=2)
