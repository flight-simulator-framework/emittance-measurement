import RF_Track as rft
try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QVBoxLayout, QDialog, QLabel, QSizePolicy
except ImportError:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QVBoxLayout, QDialog, QLabel, QSizePolicy
import numpy as np
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class EmittanceEvolution(QDialog):
    def __init__(self, interface, parent=None, screens=None):
        super().__init__(parent)
        self.setWindowTitle("Emittance evolution")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setMinimumSize(800, 500)
        self.resize(1000, 650)
        self.setSizeGripEnabled(True)
        self.interface = interface
        self.screens = list(screens or [])
        self.figure = Figure(figsize=(10, 6), constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.header = QLabel("", self)
        self.header.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        layout.addWidget(self.header, 0)
        layout.addWidget(self.canvas, 1)

    def _display_beam_evolution(self, screens = None, session = None, result = None):
        self.figure.clear()
        axes = self.figure.add_subplot(111)
        axes.set_xlabel("S [m]")
        axes.set_ylabel("Normalized emittance [mm * mrad]")
        self.canvas.draw_idle() # refreshes the graph in a popup

        if result is None:
            self.header.setText("Start optimization first.")
            self.canvas.draw_idle()
            return
        emit_x_norm = result["emit_x_norm"]
        emit_y_norm = result["emit_y_norm"]
        beta_x0 = result["beta_x0"]
        beta_y0 = result["beta_y0"]
        alpha_x0 = result["alpha_x0"]
        alpha_y0 = result["alpha_y0"]

        simulated_interface = getattr(self.interface, "tracking_interface", self.interface)

        tracking_results = simulated_interface.get_beam_evolution(quad_name = session["quad_name"], screens = session["screens"], quad_setting = float(result["quad_setting_0"]), quad_value_unit = session["quad_value_unit"], beam_parameters = result)
        print(tracking_results["emitt_x"])
        print(tracking_results["emitt_y"])
