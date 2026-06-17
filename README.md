# Home Assistant JET Cloud Integration

A custom integration for Home Assistant to monitor JET Cloud microinverters. This integration connects directly to the JET Cloud API to pull real-time telemetry, including voltage, current, and total energy production.

## Features
* **Energy Dashboard Ready**: Provides a strictly accumulating `Energy Generated Today` sensor.
* **Granular Telemetry**: Tracks individual PV string performance (Voltage, Current, Power).
* **UI Configuration**: Fully supports Home Assistant Config Flow. No YAML required.

## Installation

### Method 1: HACS (Recommended)
1. Open Home Assistant and navigate to HACS.
2. Click on "Integrations".
3. Click the three dots in the top right corner and select "Custom repositories".
4. Add the URL of this GitHub repository and select "Integration" as the category.
5. Click "Install" on the newly added JET Cloud component.
6. Restart Home Assistant.

### Method 2: Manual
1. Download the latest release from this repository.
2. Copy the `custom_components/jet_cloud` folder to your Home Assistant `config/custom_components` directory.
3. Restart Home Assistant.

## Configuration
1. Navigate to Settings > Devices & Services.
2. Click "Add Integration".
3. Search for "JET Cloud".
4. Enter the email address and password you use to log into the JET Cloud mobile app.
5. The integration will automatically discover your assigned inverters.

## Rate Limiting Warning
The default polling interval is set to 60 seconds. Do not decrease this interval. Aggressive polling will result in the JET Cloud API rate-limiting your account or temporarily blocking your IP address. If you experience repeated connection errors or frequent 401/403 responses, ensure your polling interval remains at the default value. 

## Development Note
This integration was developed with the assistance of AI. As an experienced developer, I utilized AI tools to accelerate the reverse-engineering of the intercepted API payloads and to scaffold the modern Home Assistant integration architecture. All logic, architecture decisions, and final code implementations were manually directed, reviewed, and validated to ensure robustness and compliance with Home Assistant development standards.