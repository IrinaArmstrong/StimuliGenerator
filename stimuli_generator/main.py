import sys
import re
import glob
import decimal
import json
from time import sleep
import xml.etree.ElementTree as ET
from collections import defaultdict

from typing import NoReturn
from PyQt5 import QtGui
from PyQt5.QtGui import QPainter, QBrush, QPen
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSlot, QPointF
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog,
                             QInputDialog, QPushButton, QMessageBox)

import beziers
from beziers.point import Point
from beziers.path import BezierPath
from beziers.path.representations.Nodelist import Node

import warnings

warnings.simplefilter('ignore')
warnings.filterwarnings("ignore", category=DeprecationWarning)


class Window(QMainWindow):
    # QMainWindow
    def __init__(self):
        super().__init__()
        self.title = "Stimulus Eye tracking"
        self.top = 150
        self.left = 150
        self.width = 1200
        self.height = 900
        output_dir = self.pick_directory()
        print(f"Direction chosen: {output_dir}")
        # Load all curves as svg from folder
        if not output_dir:
            output_dir = "curves"
        self.curves = self.create_curves(output_dir, verbose=False)
        # Init window and get chosen curve number
        self.init_window()
        # Translate chosen curve to points
        self.points = self.curve_as_points()
        self.point = self.points[0]
        self.save_curve_points()
        # Init painting
        self.painter = self.set_painter()

    def pick_directory(self):
        folder_path = QFileDialog.getExistingDirectory(None, 'Select a folder:', 'C:\\', QFileDialog.ShowDirsOnly)
        return folder_path

    def init_window(self):
        """
        Initialize window parameters.
        """
        self.setWindowTitle(self.title)
        self.setGeometry(self.top, self.left, self.width, self.height)
        self.curve_num = self.get_curve_choice()
        self.curve = self.curves.get(self.curve_num, 0)
        self.show_info_dialog()
        self.show()

    def show_info_dialog(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("Использование:\n\nНажмите пробел, что бы начать отрисовку стимула." \
                        "Затем следите за красной точкой до тех пор, покка она не вернется в изначальное состояние." \
                        "После чего закройте окно нажав на крестик")
        msg_box.setWindowTitle("Информация")
        msg_box.setStandardButtons(QMessageBox.Ok)
        return_value = msg_box.exec()
        if return_value == QMessageBox.Ok:
            print('OK')

    def set_painter(self):
        """
        Create and configure QPainter instance.
        :return: QPainter object.
        """
        painter = QPainter(self)
        pen = QtGui.QPen(QtCore.Qt.red, 16)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.red))
        return painter

    def create_curves(self, dir_name: str, verbose: bool):

        def parse_svg_str(svg_str: str):
            paths = [svg_part.strip(" ZM").split("L") for svg_part in re.split(r"C|L", svg_str)]
            paths = [[float(elem) for elem in elem[0].split()] for elem in paths if len(elem[0]) > 1]
            nodes = []
            for i, path in enumerate(paths):
                include_flg = "offcurve"
                if (i == 0) or (i == len(paths) - 1):
                    nodes.append(Node(x=path[0], y=path[1], type="curve"))
                else:
                    assert (len(path) == 6, "Expected Cubic Bezier curve!")
                    nodes.append(Node(x=path[0], y=path[1], type="offcurve"))
                    nodes.append(Node(x=path[2], y=path[3], type="offcurve"))
                    nodes.append(Node(x=path[4], y=path[5], type="curve"))
            del paths
            return nodes

        if len(glob.glob(dir_name + "\\*.svg")) == 0:
            print("No curves SVG files found in directory!")
            sys.exit(app.exec_())

        curves = defaultdict()
        for curve_idx, file_name in enumerate(glob.glob(dir_name + "\\*.svg")):
            if verbose:
                print(f"File: {file_name}...")
            try:
                root = ET.parse(file_name).getroot()
                path_svg = root[0][0].attrib['d']
                node_list = parse_svg_str(path_svg)
                curves[curve_idx] = BezierPath.fromNodelist(node_list)
            except SyntaxError:
                print(f"SVG file parsing error occured on file {file_name}.", file=sys.stderr)
            except AssertionError:
                print("Assertion failed!")

        if verbose and len(curves) > 0:
            for curve_idx, curve in curves.items():
                print(f"\nCurve type #{curve_idx}")
                print(f"Number of segments: {len(curve.asSegments())}")
                print(f"Curve length: {curve.length}")

        del root, path_svg, node_list
        return curves

    def get_curve_choice(self):
        c_nums = map(str, range(len(self.curves)))
        c_num, okPressed = QInputDialog.getItem(self, "Choose curve number:",
                                                "Curve number:", c_nums, 0, False)
        if okPressed and c_num:
            print(f"Chosen curve number #{c_num}")
            return int(c_num)

    def curve_as_points(self):

        def drange(x, y, jump):
            while x < y:
                yield float(x)
                x += decimal.Decimal(jump)

        length = self.curve.length
        time_step = 1 / length
        points = [self.curve.pointAtTime(t) for t in drange(0, 1, time_step)]
        return [[x, y] for (x, y) in zip([p.x for p in points], [p.y for p in points])]

    def save_curve_points(self):
        """
        Save curves points for each frame.
        """
        pp = [{"x": x, "y": y} for x, y in self.points]
        with open("results/curve#" + str(self.curve_num) + "_stimulus" + '.json', 'w', encoding='utf-8') as f:
            json.dump(pp, f, ensure_ascii=False, indent=4)

    # -------------------- DRAWING ------------------------------

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space:
            print("Starting session...")
            self.draw_points()
            print("Session finished.")

    def paintEvent(self, ev):
        self.painter.begin(self)
        pen = QtGui.QPen(QtCore.Qt.red, 16)
        pen.setCapStyle(Qt.RoundCap)
        self.painter.setPen(pen)
        self.painter.drawPoint(QPointF(self.point[0], self.point[1]))
        self.painter.end()

    def draw_points(self):
        for point in self.points:
            self.point = point
            self.repaint()
            sleep(0.01)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = Window()
    sys.exit(app.exec_())
