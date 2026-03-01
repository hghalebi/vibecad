from build123d import *

pcb_length = 70 * MM
pcb_width = 30 * MM
pcb_height = 3 * MM

with BuildPart() as pcb:
    with BuildSketch():
        Rectangle(pcb_length, pcb_width)
        for i in range(65 // 5):
            x = i * 5 - 30
            with Locations((x, -15), (x, -10), (x, 10), (x, 15)):
                Circle(1, mode=Mode.SUBTRACT)
        for i in range(30 // 5 - 1):
            y = i * 5 - 10
            with Locations((30, y), (35, y)):
                Circle(1, mode=Mode.SUBTRACT)
        with GridLocations(60, 20, 2, 2):
            Circle(2, mode=Mode.SUBTRACT)
    extrude(amount=pcb_height)
