import sys
import os
import re
import cv2
import tqdm
import json
import decimal
import numpy as np

import xml.etree.ElementTree as ET
from typing import List, Tuple

from beziers.point import Point
from beziers.path import BezierPath
from beziers.path.representations.Nodelist import Node

import warnings

warnings.simplefilter('ignore')
warnings.filterwarnings("ignore", category=DeprecationWarning)

RADIUS = 7
COLOR = (0, 0, 255)  # Red in BGR
TITLE = "Stimulus"


class Frame:

    def __init__(self, idx: int, stimuli_pos: Point,
                 h: int, w: int):
        self._idx = idx
        self._image = np.full((h, w, 3), 255, dtype=np.uint8)
        self._point = stimuli_pos
        self._height = h
        self._width = w
        self._draw()

    def _draw(self):
        # cv2.circle(image, center_coordinates, radius, color, thickness)
        self._image = cv2.circle(self._image, (int(self._point.x), int(self._point.y)),
                                 RADIUS, COLOR, -1)

    def show(self):
        """
        Displaying the frame.
        """
        cv2.imshow(TITLE, self._image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def get_image(self) -> np.ndarray:
        return self._image

    def shape(self) -> Tuple[int, int]:
        return self._image.shape


class VideoSession():

    def __init__(self, stimuli_fn: str, fps: int,
                 screen_params: Tuple[int, int]):
        self._stimuli = self.load_stimuli(stimuli_fn)
        self._fps = fps
        self._screen_params = screen_params

    def load_stimuli(self, stimuli_fn: str):
        if os.path.isfile(stimuli_fn):
            try:
                root = ET.parse(stimuli_fn).getroot()
                path_svg = root[0][0].attrib['d']
                node_list = parse_svg_str(path_svg)
                curve = BezierPath.fromNodelist(node_list)
            except SyntaxError:
                print(f"SVG file parsing error occured on file {stimuli_fn}.", file=sys.stderr)
            except AssertionError:
                print("Assertion failed!")
        return curve

    def start(self, tpf: float, out_dir: str, out_fn: str):
        points = curve_as_points(self._stimuli, tpf)
        print(
            f"Will be created {len(points)} frames from stimuli curve of length {self._stimuli.length} with FPS {self._fps}")
        if len(points) < 1:
            return
        out_path = os.path.join(out_dir, out_fn + ".avi")

        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        out_video = cv2.VideoWriter()

        success = out_video.open(out_path, fourcc, self._fps, (self._screen_params[1], self._screen_params[0]), True)
        if success:
            print(f"Started writing video to: {out_path}...")
            for idx, point in tqdm.tqdm(enumerate(points), total=len(points)):
                frame = Frame(idx, point, *self._screen_params)
                out_video.write(frame.get_image())
        else:
            print(f"Failed to open video file: {out_path}.", file=sys.stderr)

        out_video.release()
        print(f"Finished writing video.")
        save_curve_points(points, out_dir, out_fn)
        print(f"Stimulus path saved to: {os.path.join(out_dir, out_fn + '.json')}.")


# ------------------- utils ------------------------

def parse_svg_str(svg_str: str):
    paths = [svg_part.strip(" ZM").split("L") for svg_part in re.split(r"C|L", svg_str)]
    paths = [[float(elem) for elem in elem[0].split()] for elem in paths if len(elem[0]) > 1]
    nodes = []
    for i, path in enumerate(paths):
        if (i == 0) or (i == len(paths) - 1):
            nodes.append(Node(x=path[0], y=path[1], type="curve"))
        else:
            nodes.append(Node(x=path[0], y=path[1], type="offcurve"))
            nodes.append(Node(x=path[2], y=path[3], type="offcurve"))
            nodes.append(Node(x=path[4], y=path[5], type="curve"))
    del paths
    return nodes


def curve_as_points(curve: BezierPath, tpf: float) -> List[Point]:
    """
    Return curve as points.
    :param curve: BezierCurve object;
    :param tpf: time per frame (s) - speed of moving along curve;
    :return: List[Point]
    """

    def drange(x, y, jump):
        while x < y:
            yield float(x)
            x += decimal.Decimal(jump)

    time_step = 1 / (curve.length * tpf)
    points = [curve.pointAtTime(t) for t in drange(0, 1, time_step)]
    return points


def save_curve_points(points: List[Point],
                      out_dir: str, out_fn: str) -> NoReturn:
    """
    Save curves points for each frame.
    """
    pp = [{"x": point.x, "y": point.y, "idx": i} for i, point in enumerate(points)]
    with open(os.path.join(out_dir, out_fn) + '.json', 'w', encoding='utf-8') as f:
        json.dump(pp, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    vs = VideoSession("curves/curve_8.svg", fps=30, screen_params=(800, 1000))
    vs.start(tpf=0.6, out_dir="results", out_fn="curve_8")
