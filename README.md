# Emittance Measurement

Measure transverse beam emittance and Twiss parameters from quadrupole scans and beam-size measurements on downstream screens. The application varies a quadrupole setting, records the screen response, and fits a beam model to the measured scan.

You can acquire a new scan from a machine or simulation interface, or load a saved scan for analysis. The GUI shows the measured beam sizes, fitted curves, reconstructed phase spaces and emittance evolution along the beamline.

You can select and fit many other quantities, e.g. beam energy, quadrupole offsets, coupling and quadrupole strengths.
## Usage

1. Select the machine or simulation interface, the quadrupole to scan and the downstream screens to use.
2. Configure the quadrupole scan range, number of scan points and acquisition settings. Screen-specific current ranges can be adjusted when needed.
3. Acquire the scan, or load a previously recorded measurement directory.
4. Select the computing model and set bounds for the fitted beam parameters. Exclude individual scan points if they should not be included in the fit.
5. Run the fit and compare the fitted curves with the measurements. Inspect the emittance, Twiss parameters, phase-space plots and screen images.

Optional fit controls also allow quadrupole strength, transverse offset, roll and reference energy to be included in the fit, subject to the selected model's capabilities.

## Computing models

- **RFTrack tracking:** predict the screen response by tracking a beam through the machine model.
- **Linear R-response model:** use linear beam transport to calculate the scan response.
- **Machine learning model:** use a trained model for the selected machine, quadrupole and screens. If no matching model is available, the application falls back to RFTrack.

## Applications

- `Emittance_Measurement_GUI.py`: scan acquisition, loading measurements, fitting and visualization.
- `DatasetGenerator_ModelTrainer_EM_GUI.py`: generate simulated scan datasets and train the machine learning models used by the measurement GUI. Select the quadrupoles and screens, configure the dataset generation or training settings, and choose an output directory.

## Installation and startup

Use Python 3.11 or newer and Poetry 2 or newer.

```bash
git clone https://gitlab.cern.ch/flight-simulator/emittance-measurement.git
cd emittance-measurement
poetry update rf-track --lock
poetry install
poetry run python Emittance_Measurement_GUI.py
```

Poetry downloads and installs the required Python dependencies automatically.

Other entry files, using the same interpreter:

- `DatasetGenerator_ModelTrainer_EM_GUI.py`
