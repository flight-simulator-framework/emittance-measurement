from emittance_measurement.MachineLearning.ML_train import get_ml_model_file
from emittance_measurement.EmittanceComputingEngines.linear_response_engine import LinearResponseEngine
from emittance_measurement.EmittanceComputingEngines.rft_tracking_engine import RFTrackEngine
from emittance_measurement.EmittanceComputingEngines.ml_engine import MLEngine

class EmittanceComputingEngineSelector:
    @staticmethod
    def create(method, interface, session, machine_name="", info_callback=None, fallback_callback=None, **kwargs):
        method = str(method or "RFTrack tracking").strip()
        quad_name = str(session.get("quad_name", ""))
        screens = list(session.get("screens", []))

        if session.get("per_quad_sessions") and method in ("Linear R-response model", "Machine learning model"):
            if info_callback:
                info_callback(f"{method} fits one quadrupole only.")
            if fallback_callback: fallback_callback()
            method = "RFTrack tracking"

        if method == "Linear R-response model":
            if info_callback:
                info_callback("Using direct linear R-response model.")
            return LinearResponseEngine(interface)

        if method == "Machine learning model":
            model_file = get_ml_model_file(str(machine_name), quad_name, screens)

            if model_file.exists():
                if info_callback:
                    info_callback(f"Using ML model: {model_file}")
                return MLEngine(interface, quad_name=quad_name, screens=screens, machine_name=machine_name, **kwargs)

            if info_callback:
                info_callback("No ML model found. Using RFTrack instead.")

            if fallback_callback: fallback_callback()

        if info_callback:
            info_callback("Using RFTrack tracking model.")

        return RFTrackEngine(interface, **kwargs)
