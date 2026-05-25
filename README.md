# Battery Energy Cost Integration

This is a custom integration for Home Assistant that tracks the live value (in EUR) and average cost (in EUR/kWh) of the energy currently stored in your battery.

## Features
- **Continuous Cost Integration**: Accurately tracks the cost of energy entering your battery, distinguishing between Grid imports (at Nordpool prices) and PV solar generation (at 0 cost).
- **Energy Calibration**: Corrects power sensor drift by periodically calibrating against your absolute total input/output kWh sensors.
- **Auto-Reset**: Automatically resets the tracked energy value when your battery SoC reaches 0%.
- **Config Flow**: Easily configurable from the Home Assistant UI.
- **Manual Overrides**: Specify your starting cost and values, or force override them later through the Options flow.

## Installation

### HACS (Recommended)
1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Click the 3 dots in the top right corner and select **Custom repositories**.
4. Add the URL to this repository and select **Integration** as the category.
5. Click **Add**.
6. Search for "Battery Energy Cost" in HACS, click it, and download.
7. Restart Home Assistant.

### Manual
1. Copy the `custom_components/battery_energy_cost` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration
1. Go to **Settings -> Devices & Services -> Add Integration**.
2. Search for **Battery Energy Cost**.
3. The setup flow will ask for your power and energy sensors (defaulting to the Sofar battery names).
4. Optionally, supply a starting "Energy Value (EUR)" and "Average Cost (EUR/kWh)" if your battery is currently holding a charge.
5. You can always change the sensors or force a manual value override later by clicking **Configure** on the integration.
