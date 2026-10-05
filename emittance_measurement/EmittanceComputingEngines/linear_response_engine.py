import numpy as np
from emittance_measurement.EM_helpers.CheckLinearOptics import estimate_twiss_use_linear_optics_start
from emittance_measurement.EmittanceComputingEngines.AbstractComputingEngine import AbstractComputingEngine

class LinearResponseEngine(AbstractComputingEngine):

    name = "linear_r_response"
    display_name = "Linear R-response model"

    def fit_from_session(self, session, bounds=None):
        screens = list(session["screens"])
        quad_name = session["quad_name"]
        quad_setting_values = np.asarray(session["quad_setting_values"], dtype=float)
        sigx = np.asarray(session["sigx_mean"], dtype=float)
        sigy = np.asarray(session["sigy_mean"], dtype=float)
        u_x = np.asarray(session["sigx_std"], dtype=float)
        u_y = np.asarray(session["sigy_std"], dtype=float)

        gamma_rel, beta_rel, beta_gamma = self.interface.get_beam_factors()
        # R11, R12, R33, R34 from 4 test particles tracked from the quadrupole to the screens, no dataset needed
        fit = estimate_twiss_use_linear_optics_start(self.interface, quad_name, screens, quad_setting_values, sigx, sigy, u_x, u_y, np.isfinite(sigx), np.isfinite(sigy), beta_gamma)

        result = {
            "screen0": screens[0],
            "quad_name": quad_name,
            "emit_x_norm": fit["emit_x_norm"],
            "emit_y_norm": fit["emit_y_norm"],
            "emit_x_geom": fit["emit_x_norm"] / beta_gamma * 1e3, # um
            "emit_y_geom": fit["emit_y_norm"] / beta_gamma * 1e3, # um
            "beta_x0": fit["beta_x0"],
            "alpha_x0": fit["alpha_x0"],
            "beta_y0": fit["beta_y0"],
            "alpha_y0": fit["alpha_y0"],
            "fit_x_cost": fit["reduced_chi2_x"],
            "fit_y_cost": fit["reduced_chi2_y"],
            "fit_x_found": True,
            "fit_y_found": True,
            "paused": False,
            "stopped": False,
            "fit_quadrupole_strength": False,
            "fit_quad_offset": False,
            "fit_quad_roll": False,
            "quad_setting_0": float(session.get("initial_quadrupole_setting", quad_setting_values[0])),
            "fit_method": self.name,
            "prediction_observable": "sigma2",
        }

        return {
            "result": result,
            "pred_x": fit["pred_x"],
            "pred_y": fit["pred_y"],
        }
