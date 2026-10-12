import numpy as np

try:
    from PyQt6.QtCore import Qt, QRect
    from PyQt6.QtGui import QPainter
    from PyQt6.QtWidgets import QApplication, QListWidgetItem, QStyledItemDelegate
except ImportError:
    from PyQt5.QtCore import Qt, QRect
    from PyQt5.QtGui import QPainter
    from PyQt5.QtWidgets import QApplication, QListWidgetItem, QStyledItemDelegate


def _to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return np.nan


def device_name(item):
    return item.data(Qt.ItemDataRole.UserRole) or item.text()


class SPositionDelegate(QStyledItemDelegate):
    S_ROLE = int(Qt.ItemDataRole.UserRole) + 1

    def paint(self, painter: QPainter, option, index):
        painter.save()
        try:
            opt = option
            self.initStyleOption(opt, index)
            style = opt.widget.style() if opt.widget is not None else None
            if style is not None:
                opt_no_text = opt
                opt_no_text.text = ""
                style.drawControl(style.ControlElement.CE_ItemViewItem, opt_no_text, painter, opt.widget)

            device_name = str(index.data(Qt.ItemDataRole.UserRole) or index.data(Qt.ItemDataRole.DisplayRole) or "")
            s_text = str(index.data(self.S_ROLE) or "")
            r = opt.rect
            margin = 8
            painter.setFont(opt.font)
            painter.setPen(opt.palette.color(opt.palette.ColorRole.Text))

            fm = painter.fontMetrics()
            s_column_width = max(fm.horizontalAdvance("S = 000.000 m"), 90)

            left_rect = QRect(r.left() + margin, r.top(), max(10, r.width() - s_column_width - 3 * margin), r.height())
            right_rect = QRect(r.left() + r.width() - s_column_width - margin, r.top(), s_column_width, r.height())
            elided_name = fm.elidedText(device_name, Qt.TextElideMode.ElideRight, max(10, left_rect.width()))
            painter.drawText(left_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), elided_name)
            if s_text:
                painter.drawText(right_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), s_text)
        finally:
            painter.restore()


class DeviceLists:
    def _get_element_order_values(self, names):
        names = list(names)
        s_values = [_to_float(value) for value in self._get_twiss_s_positions(names)]
        if any(np.isfinite(s_values)):
            return s_values, "S"
        try:
            sequence_indices = list(self.interface.get_elements_indices(names))
        except Exception:
            sequence_indices = None
        if sequence_indices is not None and len(sequence_indices) == len(names):
            index_values = [_to_float(value) for value in sequence_indices]
            if any(np.isfinite(index_values)):
                return index_values, "index"
        return [np.nan] * len(names), ""

    def _show_s_values_and_device_lists(self, list_widget, names):
        names = list(names)
        order_values, order_kind = self._get_element_order_values(names)
        list_widget.clear()
        for name, order_value in zip(names, order_values):
            item = QListWidgetItem(str(name))
            item.setData(Qt.ItemDataRole.UserRole, str(name))
            list_widget.addItem(item)
            order_value = _to_float(order_value)
            if not np.isfinite(order_value):
                order_text = ""
            elif order_kind == "index":
                order_text = f"index = {int(order_value)}"
            else:
                order_text = f"S = {order_value:.3f} m"
            item.setData(SPositionDelegate.S_ROLE, order_text)

    def _sorted_by_s(self, names):
        names = list(names)
        order = self._get_element_order_values(names)[0]
        return [name for name, _ in sorted(zip(names, order), key=lambda pair: pair[1] if np.isfinite(pair[1]) else np.inf)]

    def _get_selection(self):
        def names(widget, selected_only):
            items = (widget.item(i) for i in range(widget.count()))
            return [device_name(item) for item in items if item.isSelected() or not selected_only]
        return (names(self.quadrupoles_list, True) or names(self.quadrupoles_list, False),
                names(self.screens_list, True) or names(self.screens_list, False))

    def _set_progress(self, value):
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(int(max(0, min(100, value))))
        QApplication.processEvents()
