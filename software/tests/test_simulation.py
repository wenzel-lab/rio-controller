#!/usr/bin/env python3
"""
Tests for simulation layer.

Verifies that simulation modules correctly mimic real hardware behavior
and that the application works identically in simulation and hardware modes.

Usage:
    python tests/test_simulation.py
    python -m tests.test_simulation
"""

import sys
import os
import unittest

# Set simulation mode
os.environ['RIO_SIMULATION'] = 'true'

# Add parent directory (software/) to path
software_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if software_dir not in sys.path:
    sys.path.insert(0, software_dir)


class TestSimulatedSPI(unittest.TestCase):
    """Test simulated SPI handler"""
    
    def setUp(self):
        """Set up test fixtures"""
        from simulation.spi_simulated import SimulatedSPIHandler, SimulatedGPIO
        self.GPIO = SimulatedGPIO
        self.spi_handler = SimulatedSPIHandler(bus=0, mode=2, speed_hz=30000, pin_mode=self.GPIO.BOARD)
    
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
        from simulation.camera_simulated import SimulatedCamera
        self.camera = SimulatedCamera()
    
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
        self.camera.start()
        frame = self.camera.get_frame_array()
        self.assertIsNotNone(frame)
        self.assertEqual(len(frame.shape), 3)  # Should be (height, width, channels)
        self.camera.stop()
    
    def test_roi_capture(self):
        """Test ROI capture"""
        self.camera.start()
        roi = (100, 100, 200, 150)
        roi_frame = self.camera.get_frame_roi(roi)
        self.assertIsNotNone(roi_frame)
        self.assertEqual(roi_frame.shape[0], roi[3])  # Height
        self.assertEqual(roi_frame.shape[1], roi[2])  # Width
        self.camera.stop()
    
    def tearDown(self):
        """Clean up"""
        try:
            self.camera.stop()
            self.camera.close()
        except:
            pass


class TestSimulatedFlow(unittest.TestCase):
    """Test simulated flow controller"""
    
    def setUp(self):
        """Set up test fixtures"""
        from simulation.flow_simulated import SimulatedFlow
        self.flow = SimulatedFlow()
    
    def test_flow_creation(self):
        """Test flow controller initialization"""
        self.assertIsNotNone(self.flow)
    
    def test_packet_handling(self):
        """Test packet handling"""
        # Test various packet types
        result = self.flow.handle_packet(0, [])  # GET_ID
        self.assertIsNotNone(result)
        
        result = self.flow.handle_packet(1, [0])  # SET_PRESSURE
        self.assertIsNotNone(result)


class TestSimulatedStrobe(unittest.TestCase):
    """Test simulated strobe controller"""
    
    def setUp(self):
        """Set up test fixtures"""
        from simulation.strobe_simulated import SimulatedStrobe
        self.strobe = SimulatedStrobe()
    
    def test_strobe_creation(self):
        """Test strobe controller initialization"""
        self.assertIsNotNone(self.strobe)
    
    def test_enable_disable(self):
        """Test strobe enable/disable"""
        result = self.strobe.handle_packet(1, [1])  # SET_ENABLE = True
        self.assertIsNotNone(result)
        
        result = self.strobe.handle_packet(1, [0])  # SET_ENABLE = False
        self.assertIsNotNone(result)
    
    def test_timing_configuration(self):
        """Test timing configuration"""
        wait_ns = 1000
        period_ns = 100000
        wait_bytes = list(wait_ns.to_bytes(4, 'little', signed=False))
        period_bytes = list(period_ns.to_bytes(4, 'little', signed=False))
        result = self.strobe.handle_packet(2, wait_bytes + period_bytes)  # SET_TIMING
        self.assertIsNotNone(result)


class TestSimulationConsistency(unittest.TestCase):
    """Test that simulation behaves consistently with real hardware"""
    
    def test_spi_api_consistency(self):
        """Test that simulated SPI has same API as real SPI"""
        from simulation.spi_simulated import SimulatedSPIHandler, SimulatedGPIO
        GPIO = SimulatedGPIO
        
        spi_handler = SimulatedSPIHandler(bus=0, mode=2, speed_hz=30000, pin_mode=GPIO.BOARD)
        
        # Should have same methods as real SPI
        self.assertTrue(hasattr(spi_handler.spi, 'xfer2'))
        self.assertTrue(hasattr(spi_handler, 'spi_select_device'))
        self.assertTrue(hasattr(spi_handler, 'spi_deselect_current'))


if __name__ == '__main__':
    unittest.main(verbosity=2)

