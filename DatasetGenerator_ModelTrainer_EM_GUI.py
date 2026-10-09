import emittance_measurement
import RF_Track as rft # do not touch this
import os, sys
from datetime import datetime
import numpy as np
try:
    pyqt_version = 6
    from PyQt6 import uic
    from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
    from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal
    from PyQt6.QtGui import QPixmap
except ImportError:
    pyqt_version = 5
    from PyQt5 import uic
    from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
    from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal
    from PyQt5.QtGui import QPixmap
from machine_interfaces.Backend.SaveOrLoad import SaveOrLoad
from emittance_measurement.MachineLearning.ML_dataset import _get_interface_initial_settings, append_dataset
from emittance_measurement.EM_helpers.DeviceLists import DeviceLists, SPositionDelegate, device_name
from emittance_measurement.MachineLearning.ML_train import TrainModel

class DatasetGeneratorWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    done = pyqtSignal()
    progress = pyqtSignal( int, int)
    log_message = pyqtSignal(str)

    def __init__(self, interface, quad_name, screens, n_samples, relative_setting_change, output_file):
        super().__init__()
        self.interface = interface
        self.quad_name = quad_name
        self.screens = screens
        self.n_samples = n_samples
        self.quad_setting_relative_change = relative_setting_change
        self.output_file = output_file
        self.stop_requested = False

    def request_stop(self):
        self.stop_requested = True

    def _emit_log(self, text):
        self.log_message.emit(str(text))

    def run(self):
        try:
            new_bounds = {
                "emit_x_norm": [3.5, 8.0],
                "beta_x0": [0.5, 3.5],
                "alpha_x0": [-3.0, 1.0],
                "emit_y_norm": [0.005, 0.2],
                "beta_y0": [6.0, 16.0],
                "alpha_y0": [-3.0, 2.0],
            }
            self._emit_log(f"Appending to dataset: {self.output_file}")
            result = append_dataset(quad_name = self.quad_name, screens = self.screens, interface = self.interface, quad_setting_relative_change = self.quad_setting_relative_change, n_samples = self.n_samples, existing_file=self.output_file, new_bounds=new_bounds)

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.done.emit()

class ModelTrainerWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    done = pyqtSignal()
    progress = pyqtSignal(int, int)
    log_message = pyqtSignal(str)

    def __init__(self, screens, quad_name, machine_name, dataset_file, model_file):
        super().__init__()
        self.screens = [str(screen) for screen in screens]
        self.quad_name = str(quad_name)
        self.machine_name = str(machine_name)
        self.dataset_file = dataset_file
        self.model_file = model_file
        self.stop_requested = False

    def request_stop(self):
        self.stop_requested = True

    def _should_stop(self):
        return bool(self.stop_requested)

    def _emit_log(self, text):
        self.log_message.emit(str(text))

    def _emit_progress(self, current, total):
        self.progress.emit(int(current), int(total))

    def run(self):
        try:
            trainer = TrainModel(
                screens=self.screens,
                quad_name=self.quad_name,
                machine_name=self.machine_name,
                dataset_file=self.dataset_file,
                model_file=self.model_file,
                log_callback=self._emit_log,
                progress_callback=self._emit_progress,
                stop_checker=self._should_stop,
            )
            metrics = trainer.train()
            self.finished.emit(metrics)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.done.emit()

class MainWindow(QMainWindow, DeviceLists, SaveOrLoad):
    def __init__(self, interface, dir_name):
        super().__init__()
        self.interface = interface
        self.dir_name = dir_name
        self.session = None
        ui_path = os.path.join(os.path.dirname(emittance_measurement.__file__), "UI files/DatasetGenerator_ModelTrainer_EM_GUI.ui")
        uic.loadUi(ui_path, self)
        self._load_logo()
        self.start_generation_button.clicked.connect(self._run_generating)
        self.stop_generation_button.clicked.connect(self._stop_generating)
        self.start_training_button.clicked.connect(self._run_training)
        self.stop_training_button.clicked.connect(self._stop_training)
        self.setWindowTitle("Emittance ML Dataset Generator")
        self.progressBar.setValue(0)
        self.quadrupoles_list.setItemDelegate(SPositionDelegate(self.quadrupoles_list))
        self.screens_list.setItemDelegate(SPositionDelegate(self.screens_list))
        self._is_running = False
        quadrupoles = list(self.interface.get_quadrupoles()["names"])
        screens_data = self.interface.get_screens()
        screens_sorted = self._sorted_by_s(screens_data["names"])
        self._show_s_values_and_device_lists(self.quadrupoles_list, quadrupoles)
        self._show_s_values_and_device_lists(self.screens_list, screens_sorted)
        self._set_progress(0)
        self.screens_list.itemSelectionChanged.connect(self._screen_selection_changed)
        self._last_selected_quadrupoles = []
        self._filter_quadrupoles_in_gui()
        self.pause_button.clicked.connect(self._pause_task)
        self.resume_button.clicked.connect(self._resume_task)
        self._pause_requested = False
        self._generation_thread = None
        self._generation_worker = None
        self._is_training = False
        self._training_thread = None
        self._training_worker = None

    def _pause_task(self):
        pass

    def _has_explicit_screen_selection(self):
        return bool(self.screens_list.selectedItems())

    def _select_all_screens_in_gui(self):
        self.screens_list.blockSignals(True)
        self.screens_list.selectAll()
        self.screens_list.blockSignals(False)
        self._filter_quadrupoles_in_gui()

    def _resume_task(self):
        if self._pause_requested:
            self.log("Resume is not yet implemented")
            self._pause_requested = False

    def _load_logo(self):
        if not hasattr(self, "logo_label"):
            return
        self.logo_label.setText("")
        self.logo_label.setScaledContents(False)

        transform_mode = (
            Qt.TransformationMode.SmoothTransformation
            if pyqt_version == 6
            else Qt.SmoothTransformation
        )
        base_dir = os.path.dirname(emittance_measurement.__file__)
        logo_path = os.path.join(base_dir, "UI files", "Assets", "CERN_logo.png")
        if not os.path.isfile(logo_path):
            return
        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            return
        scaled = pixmap.scaledToHeight(80, transform_mode)
        self.logo_label.setPixmap(scaled)
        self.logo_label.setToolTip(logo_path)

    def _get_machine_ml_folder_name(self):
        interface_defaults = _get_interface_initial_settings(self.interface)

        if interface_defaults is not None:
            machine_name = interface_defaults.get("machine")
            if machine_name:
                return str(machine_name)

        return type(self.interface).__name__

    def _get_default_output_dir(self, quad_name, screens):
        if len(screens) == self.screens_list.count():
            screens_folder = "all_screens"
        else:
            screens_folder = "screens_" + "-".join(str(screen) for screen in screens)

        return os.path.join(
            os.path.dirname(emittance_measurement.__file__),
            "MachineLearning",
            self._get_machine_ml_folder_name(),
            str(quad_name),
            screens_folder,
        )


    def _screen_selection_changed(self):
        self._filter_quadrupoles_in_gui()

    def _filter_quadrupoles_in_gui(self):
        previously_selected = [device_name(self.quadrupoles_list.item(i)) for i in range(self.quadrupoles_list.count()) if self.quadrupoles_list.item(i).isSelected()]

        if previously_selected:
            self._last_selected_quadrupoles = list(previously_selected)
        else:
            self._last_selected_quadrupoles = list(getattr(self, "_last_selected_quadrupoles", []))

        _, selected_screens = self._get_selection()
        if not selected_screens:
            return

        screen_position, screen_order_kind = self._get_element_order_values(selected_screens)
        finite_screen_positions = [float(s) for s in screen_position if np.isfinite(s)]
        if not finite_screen_positions:
            return

        first_screen_position = min(finite_screen_positions)
        last_screen_position = max(finite_screen_positions)
        all_quadrupoles = list(self.interface.get_quadrupoles().get("names", []))
        quad_order, quad_order_kind = self._get_element_order_values(all_quadrupoles)

        if quad_order_kind != screen_order_kind: # S [m] or index
            return

        quad_pos = {name: float(s) for name, s in zip(all_quadrupoles, quad_order) if np.isfinite(s)}

        before_last_screen_quads = [
            name for name in all_quadrupoles
            if name in quad_pos and quad_pos[name] < last_screen_position
        ]

        valid_previous = [q for q in getattr(self, "_last_selected_quadrupoles", []) if q in before_last_screen_quads]
        upstream_to_first_screen_quads = [name for name in before_last_screen_quads if quad_pos[name] < first_screen_position]

        self.quadrupoles_list.blockSignals(True)
        self._show_s_values_and_device_lists(self.quadrupoles_list, before_last_screen_quads)

        if valid_previous:
            for i in range(self.quadrupoles_list.count()):
                item = self.quadrupoles_list.item(i)
                if device_name(item) in valid_previous:
                    item.setSelected(True)
            self._last_selected_quadrupoles = list(valid_previous)
        elif upstream_to_first_screen_quads:
            closest_quad = max(upstream_to_first_screen_quads, key=lambda name: quad_pos[name])
            for i in range(self.quadrupoles_list.count()):
                item = self.quadrupoles_list.item(i)
                if device_name(item) == closest_quad:
                    item.setSelected(True)
                    self._last_selected_quadrupoles = [closest_quad]
                    break
        elif self.quadrupoles_list.count() > 0:
            item = self.quadrupoles_list.item(0)
            if item is not None:
                item.setSelected(True)
                self._last_selected_quadrupoles = [device_name(item)]
        else:
            self._last_selected_quadrupoles = []

        self.quadrupoles_list.blockSignals(False)

    def _get_twiss_s_positions(self, names):
        names = list(names)
        positions = [np.nan] * len(names)
        if not hasattr(self.interface, "_get_elements_positions"):
            return positions

        try:
            pos = self.interface._get_elements_positions()
            pos_names = list(pos.get("names", []))
            s = np.asarray(pos.get("S", []), dtype=float)
            lookup = {
                name: float(s[i])
                for i, name in enumerate(pos_names)
                if i < s.size and np.isfinite(s[i])
            }
            positions = [lookup.get(name, np.nan) for name in names]
        except Exception:
            positions = [np.nan] * len(names)
        return positions

    def _run_generating(self):
        if self._is_running:
            self.log("Dataset generation already running")
            return
        if self.screens_list.count() == 0:
            QMessageBox.warning(self, "Error", "No screens available.")
            return

        if not self._has_explicit_screen_selection():
            self._select_all_screens_in_gui()

        quadrupoles, screens = self._get_selection()

        if not quadrupoles:
            QMessageBox.warning(self, "Error", "No quadrupole selected.")
            return

        if not screens:
            QMessageBox.warning(self, "Error", "No screens selected.")
            return

        quad_name = quadrupoles[0]
        relative_setting_change = (float(self.quad_setting_relative_min_spin.value()), float(self.quad_setting_relative_max_spin.value()))
        if relative_setting_change[0] >= relative_setting_change[1]:
            QMessageBox.warning(self, "Error", "The minimum relative quadrupole setting must be smaller than the maximum.")
            return
        n_samples = int(self.samples_spin.value())
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            output_dir = self._get_default_output_dir(quad_name, screens)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "EM_dataset.npz")
        self.log(f"Dataset output directory: {output_dir}")
        self._is_running = True
        self._set_progress(0)
        self.progressBar.setFormat("Dataset generation: 0/0")
        self.log(f"Starting dataset generation for {quad_name}...")

        thread = QThread(self)
        worker = DatasetGeneratorWorker(
            interface=self.interface,
            quad_name=quad_name,
            screens=screens,
            n_samples=n_samples,
            relative_setting_change=relative_setting_change,
            output_file=output_file,
        )
        worker.moveToThread(thread)
        worker.log_message.connect(self.log)
        worker.progress.connect(self._on_generation_progress)
        worker.finished.connect(self._on_generation_finished)
        worker.error.connect(self._on_generation_error)
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(self._on_generation_thread_finished)
        thread.finished.connect(thread.deleteLater)
        thread.started.connect(worker.run)

        self._generation_thread = thread
        self._generation_worker = worker
        thread.start()

    def _on_generation_progress(self, current, total):
        total = max(int(total), 1)
        current = max(0, min(int(current), total))
        self._set_progress(current / total * 100)
        self.progressBar.setFormat(f"Dataset generation: {current}/{total}")

    def _on_generation_finished(self, result):
        self._set_progress(100)
        self.progressBar.setFormat("Dataset generation finished")
        self.log(f"Finished generating dataset: {result}")
        QMessageBox.information(self, "Finished", "Dataset generation finished.")

    def _on_generation_error(self, message):
        self._set_progress(0)
        self.log(f"Error in generating dataset. {message}")
        QMessageBox.information(self, "Error", f"Error in generating dataset. {message}")

    def _stop_generating(self):
        self.log("Stopping dataset generation requested.")
        if self._generation_worker is not None:
            self._generation_worker.request_stop()

    def _on_generation_thread_finished(self):
        self._is_running = False
        self._generation_thread = None
        self._generation_worker = None

    def _run_training(self):
        if self._is_training:
            self.log("Model training already running", "model_training_log")
            return

        quadrupoles, screens = self._get_selection()
        if not quadrupoles:
            QMessageBox.warning(self, "Error", "No quadrupole selected.")
            return
        if not screens:
            QMessageBox.warning(self, "Error", "No screens selected.")
            return

        quad_name = quadrupoles[0]
        output_dir = self.output_dir_edit.text().strip() or self._get_default_output_dir(quad_name, screens)
        dataset_file = os.path.join(output_dir, "EM_dataset.npz")
        model_file = os.path.join(output_dir, "EM_model.pt")
        if not os.path.isfile(dataset_file):
            QMessageBox.warning(self, "Error", f"Dataset not found: {dataset_file}")
            return

        self._is_training = True
        self.progressBar.setFormat("Model training: 0/0")
        self.log(f"Starting model training for {quad_name}...", "model_training_log")

        thread = QThread(self)
        worker = ModelTrainerWorker(
            screens=screens,
            quad_name=quad_name,
            machine_name=self._get_machine_ml_folder_name(),
            dataset_file=dataset_file,
            model_file=model_file,
        )
        worker.moveToThread(thread)
        worker.log_message.connect(lambda text: self.log(text, "model_training_log"))
        worker.progress.connect(self._on_training_progress)
        worker.finished.connect(self._on_training_finished)
        worker.error.connect(self._on_training_error)
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(self._on_training_thread_finished)
        thread.finished.connect(thread.deleteLater)
        thread.started.connect(worker.run)

        self._training_thread = thread
        self._training_worker = worker
        thread.start()

    def _on_training_progress(self, current, total):
        total = max(int(total), 1)
        current = max(0, min(int(current), total))
        self._set_progress(current / total * 100)
        self.progressBar.setFormat(f"Model training: {current}/{total}")

    def _on_training_finished(self, metrics):
        self._set_progress(100)
        self.progressBar.setFormat("Model training finished")
        self.log(f"Finished training model: {metrics}", "model_training_log")
        QMessageBox.information(self, "Finished", "Model training finished.")

    def _on_training_error(self, message):
        self._set_progress(0)
        self.log(f"Error in training model. {message}", "model_training_log")
        QMessageBox.information(self, "Error", f"Error in training model. {message}")

    def _stop_training(self):
        self.log("Stopping model training requested.", "model_training_log")
        if self._training_worker is not None:
            self._training_worker.request_stop()

    def _on_training_thread_finished(self):
        self._is_training = False
        self._training_thread = None
        self._training_worker = None

    def log(self, text, widget_name="log_console"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {text}"
        widget = getattr(self, widget_name, None)
        if widget is not None:
            widget.appendPlainText(line)
        else:
            print(line)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    from machine_interfaces.Backend import SelectInterface
    interface = SelectInterface.choose_acc_and_interface()

    if interface is None:
        sys.exit(0)

    project_name = (
        interface.get_name()
        if hasattr(interface, "get_name")
        else type(interface).__name__
    )

    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = os.path.expanduser(f"~/CERN-Flight_Simulator-Data/EM_{project_name}{time_str}")

    w = MainWindow(interface, dir_name)
    w.show()
    sys.exit(app.exec())
