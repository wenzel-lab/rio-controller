#!/usr/bin/env python3
"""
Tests for simulation layer.

Verifies that simulation modules correctly mimic real hardware behavior
and that the application works identically in simulation and hardware modes.

Usage:
    python tests/test_simulation.py
    python -m tests.test_simulation
"""

import os
import unittest

# Set simulation mode
os.environ["RIO_SIMULATION"] = "true"


class TestSimulatedSPI(unittest.TestCase):
    """Test simulated SPI handler"""

    def setUp(self):
        """Set up test fixtures"""
        from simulation.spi_simulated import SimulatedSPIHandler, SimulatedGPIO

        self.GPIO = SimulatedGPIO
        self.spi_handler = SimulatedSPIHandler(
            bus=0, mode=2, speed_hz=30000, pin_mode=self.GPIO.BOARD
        )

    def test_spi_handler_creation(self):
        """Test SPI handler initialization"""
        self.assertIsNotNone(self.spi_handler)
        self.assertIsNotNone(self.spi_handler.spi)

    def test_spi_transfer(self):
        """Test SPI data transfer"""
        data_out = [0x01, 0x02, 0x03]
        data_in = self.spi_handler.spi.xfer2(data_out)
        self.assertEqual(len(data_in), len(data_out))

    def test_gpio_setup(self):
        """Test GPIO port setup"""
        self.GPIO.setmode(self.GPIO.BOARD)
        self.spi_handler.initialize_port(31, self.GPIO.OUT, initial=self.GPIO.HIGH)
        # Should not raise exception

    def test_device_selection(self):
        """Test device selection via GPIO"""
        self.GPIO.setmode(self.GPIO.BOARD)
        self.spi_handler.initialize_port(31, self.GPIO.OUT, initial=self.GPIO.HIGH)
        self.spi_handler.spi_select_device(31)
        self.spi_handler.spi_deselect_current()


class TestSimulatedCamera(unittest.TestCase):
    """Test simulated camera"""

    def setUp(self):
        """Set up test fixtures"""
        try:
            from simulation.camera_simulated import SimulatedCamera
        except ImportError as e:
            self.skipTest(f"Camera simulation requires numpy/opencv: {e}")

        self.camera = SimulatedCamera()  # SimulatedCamera doesn't require device_port

    def test_camera_creation(self):
        """Test camera initialization"""
        self.assertIsNotNone(self.camera)

    def test_camera_start_stop(self):
        """Test camera start/stop"""
        self.camera.start()
        self.assertTrue(self.camera.running)

        self.camera.stop()
        self.assertFalse(self.camera.running)

    def test_frame_generation(self):
        """Test frame generation"""
        import time

        self.camera.start()
        # Wait a bit for frame generation thread to produce first frame
        time.sleep(0.1)
        frame = self.camera.get_frame_array()
        self.assertIsNotNone(frame)
        if frame is not None:
            self.assertEqual(len(frame.shape), 3)  # Should be (height, width, channels)
        self.camera.stop()

    def test_roi_capture(self):
        """Test ROI capture"""
        self.camera.start()
        # Wait a bit for frame generation
        import time

        time.sleep(0.1)
        # ROI format: (x, y, width, height)
        roi = (100, 100, 200, 150)
        roi_frame = self.camera.get_frame_roi(roi)
        self.assertIsNotNone(roi_frame)
        # Check dimensions (height, width)
        if roi_frame is not None:
            self.assertEqual(roi_frame.shape[0], roi[3])  # Height
            self.assertEqual(roi_frame.shape[1], roi[2])  # Width
        self.camera.stop()

    def tearDown(self):
        """Clean up"""
        try:
            self.camera.stop()
            self.camera.close()
        except Exception:
            pass


class TestSimulatedFlow(unittest.TestCase):
    """Test simulated flow controller"""

    def setUp(self):
        """Set up test fixtures"""
        from simulation.flow_simulated import SimulatedFlow
        from drivers.spi_handler import PORT_FLOW

        self.flow = SimulatedFlow(device_port=PORT_FLOW)

    def test_flow_creation(self):
        """Test flow controller initialization"""
        self.assertIsNotNone(self.flow)

    def test_packet_handling(self):
        """Test packet handling"""
        # Test various packet types using packet_query
        valid, result = self.flow.packet_query(self.flow.PACKET_TYPE_GET_ID, [])
        self.assertIsNotNone(result)
        self.assertIsInstance(valid, bool)

        # Test SET_PRESSURE_TARGET (requires proper data format)
        valid, result = self.flow.packet_query(
            self.flow.PACKET_TYPE_SET_PRESSURE_TARGET, [1, 0, 0]  # mask=1, pressure=0
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(valid, bool)


class TestSimulatedStrobe(unittest.TestCase):
    """Test simulated strobe controller"""

    def setUp(self):
        """Set up test fixtures"""
        from simulation.strobe_simulated import SimulatedStrobe
        from drivers.spi_handler import PORT_STROBE

        self.strobe = SimulatedStrobe(device_port=PORT_STROBE)

    def test_strobe_creation(self):
        """Test strobe controller initialization"""
        self.assertIsNotNone(self.strobe)

    def test_enable_disable(self):
        """Test strobe enable/disable"""
        # Use packet_query which calls packet_write internally
        valid, response = self.strobe.packet_query(self.strobe.PACKET_TYPE_SET_ENABLE, [1])
        self.assertTrue(valid)
        self.assertTrue(self.strobe.enabled)

        valid, response = self.strobe.packet_query(self.strobe.PACKET_TYPE_SET_ENABLE, [0])
        self.assertTrue(valid)
        self.assertFalse(self.strobe.enabled)

    def test_timing_configuration(self):
        """Test timing configuration"""
        wait_ns = 1000
        period_ns = 100000
        wait_bytes = list(wait_ns.to_bytes(4, "little", signed=False))
        period_bytes = list(period_ns.to_bytes(4, "little", signed=False))
        valid, response = self.strobe.packet_query(
            self.strobe.PACKET_TYPE_SET_TIMING, wait_bytes + period_bytes
        )
        self.assertTrue(valid)
        self.assertEqual(self.strobe.wait_ns, wait_ns)
        self.assertEqual(self.strobe.period_ns, period_ns)


class TestSimulationConsistency(unittest.TestCase):
    """Test that simulation behaves consistently with real hardware"""

    def test_spi_api_consistency(self):
        """Test that simulated SPI has same API as real SPI"""
        from simulation.spi_simulated import SimulatedSPIHandler, SimulatedGPIO

        GPIO = SimulatedGPIO

        spi_handler = SimulatedSPIHandler(bus=0, mode=2, speed_hz=30000, pin_mode=GPIO.BOARD)

        # Should have same methods as real SPI
        self.assertTrue(hasattr(spi_handler.spi, "xfer2"))
        self.assertTrue(hasattr(spi_handler, "spi_select_device"))
        self.assertTrue(hasattr(spi_handler, "spi_deselect_current"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
