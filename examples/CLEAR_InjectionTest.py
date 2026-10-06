"""Injection test: simulate a CLEAR quad scan with known errors, then fit it with growing sets of extra parameters."""
import sys, io, contextlib
import numpy as np
import RF_Track as rft
from machine_interfaces_clear.InterfaceCLEAR_RFTrack_Errors import InterfaceCLEAR_RFTrack_Errors
from machine_interfaces_clear.interface_setup import INTERFACES
from emittance_measurement.EM_helpers.QuadrupoleModelUpdate import load_model_quadrupoles
from emittance_measurement.EM_helpers.Optimization import Optimization

STATUS = "/Users/wiktoriamalek/CERN-Flight_Simulator-Data/AllCLEARfiles/Quadrupole_Scans/CA_QFD_0360/BestScans/Quadrupole_scan_CLEAR_CA.QFD0360_20260908_163219/quadrupoles_status.npz"
QUAD, NSHOTS = "CA.QFD0360", 10
RANGES = {"CA.BTV0390H": (0, 140), "CA.BTV0620": (0, 50), "CA.BTV0730": (0, 50)}  # same as the real scan, BTV0910 left out
ERRORS = dict(quad_scale=1.03, quad_dx=0.5e-3, quad_dy=-0.3e-3, energy_pref=194.0)  # set quad_scale=1, offsets 0, energy 198 for a null test
FITS = {"none": {}, "strength": dict(fit_quadrupole_strength=True), "energy": dict(fit_energy_pref=True),
        "strength+energy": dict(fit_quadrupole_strength=True, fit_energy_pref=True),
        "strength+energy+offset": dict(fit_quadrupole_strength=True, fit_energy_pref=True, fit_quad_offset=True)}

I = InterfaceCLEAR_RFTrack_Errors(seed=int(sys.argv[1]) if len(sys.argv) > 1 else 0, **ERRORS)
load_model_quadrupoles(I, STATUS)

# Truth: beam at the entrance of the scanned quad, tracked through the erroneous machine
seq = I.get_sequence()
first = lambda lattice, name, k: lattice[name][k] if isinstance(lattice[name], list) else lattice[name]
lattice = I.true_lattice()
truth = rft.Lattice_view(lattice, first(lattice, seq[0], 0), first(lattice, seq[seq.index(QUAD) - 1], -1)).track(I.true_beam()).get_info()

# Simulated scan, laid out like the GUI session: one row per distinct current, NaN where a screen was not measured
screens = list(RANGES)
per_screen = {s: np.linspace(*RANGES[s], 21) for s in screens}
currents = np.unique(np.concatenate(list(per_screen.values())))
shots = {k: np.full((currents.size, len(screens), NSHOTS), np.nan) for k in ("sigx", "sigy", "x", "y", "sigxy")}
for j, screen in enumerate(screens):
    for current in per_screen[screen]:
        i = np.searchsorted(currents, current)
        I.set_quadrupoles([QUAD], [current], track=False)
        for k in range(NSHOTS):
            data = I.get_screens([screen])
            for key in shots: shots[key][i, j, k] = data[key][0]
I0 = float(np.median(currents))
session = dict(screens=screens, quad_name=QUAD, quad_setting_values=currents, initial_quadrupole_setting=I0,
               **{f"{key}_shots": value for key, value in shots.items()},
               sigx_mean=np.nanmedian(shots["sigx"], 2), sigy_mean=np.nanmedian(shots["sigy"], 2))

bounds = {k: v for k, v in next(s for s in INTERFACES if s["class_name"] == "InterfaceCLEAR_RFTrack")["bounds"].items()}
bounds.update(quad_setting_0=[0.7 * I0, 1.3 * I0], quad_dx0=[-2e-3, 2e-3], quad_dy0=[-2e-3, 2e-3])

print(f"{'fit':24s} {'chi2':>9s} {'N':>4s} {'chi2/ndf':>8s} | {'eps_x':>13s} {'eps_y':>13s} {'beta_x':>7s} {'alpha_x':>7s} {'beta_y':>7s} {'alpha_y':>7s} | {'scale':>14s} {'E [MeV/c]':>14s} {'dx [mm]':>14s} {'dy [mm]':>14s}")
print(f"{'TRUTH':24s} {'':>9s} {'':>4s} {'':>8s} | {truth.emitt_x:13.2f} {truth.emitt_y:13.2f} {truth.beta_x:7.2f} {truth.alpha_x:7.2f} {truth.beta_y:7.2f} {truth.alpha_y:7.2f} | "
      f"{ERRORS['quad_scale']:14.3f} {ERRORS['energy_pref']:14.1f} {ERRORS['quad_dx'] * 1e3:14.2f} {ERRORS['quad_dy'] * 1e3:14.2f}")
pm = lambda r, k, scale=1.0: f"{r[k] * scale:.3f}±{r[k + '_err'] * scale:.3f}" if np.isfinite(r.get(k, np.nan)) else "-"
for name, flags in FITS.items():
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        r = Optimization(I, **flags).fit_from_session(session, {k: v for k, v in bounds.items() if k not in ("quad_setting_0", "quad_dx0", "quad_dy0", "energy_pref")
                                                                 or (k == "quad_setting_0" and flags.get("fit_quadrupole_strength"))
                                                                 or (k.startswith("quad_d") and flags.get("fit_quad_offset"))
                                                                 or (k == "energy_pref" and flags.get("fit_energy_pref"))})["result"]
    chi2 = float(next(l for l in reversed(log.getvalue().splitlines()) if "chi2 (minimized)" in l).split(":")[-1])
    n = int(np.isfinite(shots["sigx"][..., 0]).sum()) * (4 if flags.get("fit_quad_offset") else 2)
    npar = 6 + sum(map(bool, flags.values())) + bool(flags.get("fit_quad_offset"))
    scale = f"{r['quad_setting_0'] / I0:.3f}±{r['quad_setting_0_err'] / I0:.3f}" if flags.get("fit_quadrupole_strength") else "-"
    print(f"{name:24s} {chi2:9.1f} {n:4d} {chi2 / (n - npar):8.2f} | {pm(r, 'emit_x_norm'):>13s} {pm(r, 'emit_y_norm'):>13s} {r['beta_x0']:7.2f} {r['alpha_x0']:7.2f} {r['beta_y0']:7.2f} {r['alpha_y0']:7.2f} | "
          f"{scale:>14s} {pm(r, 'energy_pref'):>14s} {pm(r, 'quad_dx0'):>14s} {pm(r, 'quad_dy0'):>14s}", flush=True)
