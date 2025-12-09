# Simulation Setup - Final Steps

## ✅ What's Fixed

1. ✅ All hardware import errors resolved (`spidev`, `RPi.GPIO`, `picamera`)
2. ✅ Missing flow control methods added (`get_flow_target`, `set_flow`, `get_flow_pid_consts`)
3. ✅ Verbose logging reduced (only important messages shown)
4. ✅ Import paths fixed for simulation module
5. ✅ Configuration file created (`rio-config.yaml`)

## ⚠️ Final Step: Install Missing Dependencies

The simulation requires numpy and opencv-python for the camera simulation:

```bash
# Activate environment
mamba activate rio-simulation

# Install missing dependencies
pip install numpy opencv-python
```

## 🚀 Run the Webapp

After installing dependencies:

```bash
# Make sure you're in the environment
mamba activate rio-simulation

# Enable simulation mode
export RIO_SIMULATION=true

# Run webapp
cd user-interface-software/src/webapp
python pi_webapp.py
```

## Expected Output

You should see:
```
[SimulatedSPIHandler] Initialized (bus=0, mode=2, speed=30000Hz)
[picommon] Using simulated SPI/GPIO (simulation mode)
[SimulatedCamera] Started (640x480 @ 30 FPS)
 * Running on http://0.0.0.0:5000
```

Then open your browser to: **http://localhost:5000**

## What You'll See in the GUI

- ✅ Camera feed with synthetic droplets (moving circles)
- ✅ Strobe controls
- ✅ Flow controls (4 channels)
- ✅ ROI selection interface (draw rectangle on camera image)
- ✅ All controls functional (simulated)

## Troubleshooting

### "ModuleNotFoundError: No module named 'numpy'"
**Solution:** Install dependencies:
```bash
pip install numpy opencv-python
```

### "Simulation module unavailable"
**Solution:** Make sure `RIO_SIMULATION=true` is set and you're in the correct directory

### GUI doesn't load
**Solution:** 
- Check that Flask is running (look for "Running on http://0.0.0.0:5000")
- Try `http://127.0.0.1:5000` instead of `localhost:5000`
- Check browser console for errors

---

**Status:** Ready to run after installing numpy/opencv-python!

