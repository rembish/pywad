from PIL import Image
from PIL.ImageDraw import ImageDraw

from .lumps.map import BaseMapEntry


class MapExporter:
    def __init__(self, map_entry: BaseMapEntry) -> None:
        self.level = map_entry
        self.im = Image.new("RGB", size=(10000, 10000))
        self.draw = ImageDraw(self.im)

    def process(self) -> None:
        off = self.level.boundaries[0]
        for thing in self.level.things or []:
            x = thing.x - off.x
            y = thing.y - off.y
            self.draw.ellipse([x - 20, y - 20, x + 20, y + 20], fill="#ffffff")

    def show(self) -> None:
        self.im.show()
