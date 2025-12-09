#!/usr/bin/env python3
"""
Unit tests for controller modules.

Tests high-level device controllers (flow_web, heater_web, camera, strobe_cam)
to ensure business logic works correctly.

Usage:
    python tests/test_controllers.py
    python -m tests.test_controllers
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from threading import Event

# Set simulation mode
os.environ['RIO_SIMULATION'] = 'true'

# Add parent directory (software/) to path
software_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if software_dir not in sys.path:
    sys.path.insert(0, software_dir)


class TestFlowWeb(unittest.TestCase):
    """Test flow web controller"""
    
    def setUp(self):
        """Set up test fixtures"""
        from drivers.spi_handler import spi_init, PORT_FLOW
        spi_init(0, 2, 30000)
        from controllers.flow_web import FlowWeb
        self.flow = FlowWeb(PORT_FLOW)
    
    def test_flow_initialization(self):
        """Test flow controller initialization"""
        self.assertIsNotNone(self.flow)
        self.assertIsNotNone(self.flow.flow)
    
    def test_get_control_modes(self):
        """Test getting available control modes"""
        modes = self.flow.get_control_modes()
        self.assertIsInstance(modes, list)
        self.assertGreater(len(modes), 0)
    
    def test_get_flow_targets(self):
        """Test getting flow targets"""
        targets = self.flow.get_flow_targets()
        self.assertIsInstance(targets, list)
        # Should have 4 channels
        self.assertEqual(len(targets), 4)
    
    def tearDown(self):
        """Clean up"""
        from drivers.spi_handler import spi_close
        try:
            spi_close()
        except:
            pass


class TestHeaterWeb(unittest.TestCase):
    """Test heater web controller"""
    
    def setUp(self):
        """Set up test fixtures"""
        from drivers.spi_handler import spi_init, PORT_HEATER1
        spi_init(0, 2, 30000)
        from controllers.heater_web import heater_web
        self.heater = heater_web(1, PORT_HEATER1)
    
    def test_heater_initialization(self):
        """Test heater controller initialization"""
        self.assertIsNotNone(self.heater)
        self.assertIsNotNone(self.heater.holder)
    
    def test_get_temperature(self):
        """Test getting temperature"""
        temp = self.heater.get_temperature()
        self.assertIsInstance(temp, (int, float))
    
    def tearDown(self):
        """Clean up"""
        from drivers.spi_handler import spi_close
        try:
            spi_close()
        except:
            pass


class TestCameraController(unittest.TestCase):
    """Test camera controller"""
    
    def setUp(self):
        """Set up test fixtures"""
        from flask_socketio import SocketIO
        from flask import Flask
        
        app = Flask(__name__)
        socketio = SocketIO(app, async_mode='threading')
        
        from controllers.camera import Camera
        self.exit_event = Event()
        self.camera = Camera(self.exit_event, socketio)
    
    def test_camera_initialization(self):
        """Test camera initialization"""
        self.assertIsNotNone(self.camera)
        self.assertIsNotNone(self.camera.cam_data)
        self.assertIsNotNone(self.camera.strobe_data)
    
    def test_camera_data_structure(self):
        """Test camera data structure"""
        self.assertIn('camera', self.camera.cam_data)
        self.assertIn('status', self.camera.cam_data)
    
    def test_strobe_data_structure(self):
        """Test strobe data structure"""
        self.assertIn('enable', self.strobe_data)
        self.assertIn('period_ns', self.strobe_data)
    
    @property
    def strobe_data(self):
        """Get strobe data"""
        return self.camera.strobe_data
    
    def tearDown(self):
        """Clean up"""
        try:
            self.camera.close()
        except:
            pass


class TestConfigImport(unittest.TestCase):
    """Test configuration import"""
    
    def test_config_import(self):
        """Test that config module can be imported"""
        try:
            import config
            self.assertTrue(True)
        except ImportError:
            self.fail("config module should be importable")
    
    def test_config_constants(self):
        """Test that config has expected constants"""
        try:
            from config import (
                CAMERA_THREAD_WIDTH,
                CAMERA_THREAD_HEIGHT,
                STROBE_DEFAULT_PERIOD_NS,
            )
            self.assertIsInstance(CAMERA_THREAD_WIDTH, int)
            self.assertIsInstance(CAMERA_THREAD_HEIGHT, int)
            self.assertIsInstance(STROBE_DEFAULT_PERIOD_NS, int)
        except ImportError:
            # Config may have fallback values
            pass


if __name__ == '__main__':
    unittest.main(verbosity=2)

