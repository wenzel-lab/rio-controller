# Disabling Flow and Heater Tabs in Rio Controller

To hide the Flow Control and Heater tabs in the Rio Controller web interface, you can disable them via environment variables or configuration files.

## Method 1: Environment Variables (Recommended)

Set these environment variables before starting the application:

```bash
export RIO_FLOW_ENABLED=false
export RIO_HEATER_ENABLED=false
```

Then start the application as usual. The tabs will be hidden from the interface.

## Method 2: Configuration File

Edit your configuration YAML file (e.g., `rio-config.yaml`) and set:

```yaml
# Flow controller configuration
flow:
  enabled: false  # Disable flow controller

# Heater configuration
heater:
  enabled: false  # Disable heaters
```

Note: The environment variables take precedence over the configuration file settings.

## Verification

After setting these values and restarting the application:
- The **Flow Control** tab will not appear in the navigation
- The **Heater** tab will not appear in the navigation
- Only the **Camera View**, **Camera Config**, and **Droplet Detection** (if enabled) tabs will be visible

## Re-enabling

To re-enable the tabs later, either:
- Set the environment variables to `true`:
  ```bash
  export RIO_FLOW_ENABLED=true
  export RIO_HEATER_ENABLED=true
  ```
- Or set `enabled: true` in the configuration file
- Then restart the application

## Complete Command List

For a strobe-only configuration (camera + strobe, no flow/heaters):

```bash
# Disable flow and heaters
export RIO_FLOW_ENABLED=false
export RIO_HEATER_ENABLED=false

# Start the application (example)
python main.py
```

Or in a single command:

```bash
RIO_FLOW_ENABLED=false RIO_HEATER_ENABLED=false python main.py
```

## Configuration File Example

For a minimal camera + strobe configuration, your `rio-config.yaml` should have:

```yaml
# Camera configuration
camera:
  type: rpi  # or rpi_hq, mako
  # ... other camera settings

# Strobe configuration
strobe:
  enabled: true
  default_period_ns: 20000  # 20 microseconds
  # ... other strobe settings

# Flow controller - DISABLED
flow:
  enabled: false

# Heater - DISABLED
heater:
  enabled: false

# Droplet detection (optional)
droplet_detection:
  enabled: true  # or false if not needed
```

