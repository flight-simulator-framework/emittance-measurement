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

On a control-room computer, install the applications with the deployment script of your machine: [CLEAR](https://gitlab.cern.ch/flight-simulator/machine-interfaces/-/blob/master/backends/clear/clear_deploy.md), [ATF2](https://gitlab.cern.ch/flight-simulator/machine-interfaces/-/blob/master/backends/atf2/atf2_deploy.md), [ESRF](https://gitlab.cern.ch/flight-simulator/machine-interfaces/-/blob/master/backends/esrf/esrf_deploy.md) or [FACET2](https://gitlab.cern.ch/flight-simulator/machine-interfaces/-/blob/master/backends/facet2/facet2_deploy.md). It creates a shared virtual environment and one launcher per GUI, e.g. `./Emittance_Measurement_GUI.sh`.

For a local installation, use Python 3.11 or newer and keep the repositories in one directory:

```bash
git clone https://gitlab.cern.ch/flight-simulator/machine-interfaces.git
git clone https://gitlab.cern.ch/flight-simulator/response-matrix.git
git clone https://gitlab.cern.ch/flight-simulator/emittance-measurement.git
python3 -m venv venv
source venv/bin/activate
pip install -e machine-interfaces -e machine-interfaces/backends/esrf -e response-matrix -e emittance-measurement
cd emittance-measurement
python Emittance_Measurement_GUI.py
```

Replace `esrf` with `atf2` or `facet2` for another machine. The CLEAR control-system packages are available only from the CERN Acc-Py index; elsewhere, install only the CLEAR simulation:

```bash
pip install rf-track cpymad
pip install --no-deps -e machine-interfaces/backends/clear
```

Editable installs pick up `git pull` changes without reinstalling.

Other entry files, using the same environment:

- `DatasetGenerator_ModelTrainer_EM_GUI.py`
