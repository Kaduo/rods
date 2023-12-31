import threading
from enum import Enum
from argparse import ArgumentParser

import pyglet
import pyhaptic
from pyglet import shapes

parser = ArgumentParser()
parser.add_argument("-H", "--haptic", help="Enable haptic", action="store_true", default=False)
parser.add_argument("-f", "--fps", help="Show fps", action="store_true", default=True)
args = parser.parse_args()

window = pyglet.window.Window(fullscreen=True)
fps_display = pyglet.window.FPSDisplay(window=window)

rods_batch = pyglet.graphics.Batch()
menu_rods_batch = pyglet.graphics.Batch()


colors = {
    "white": (238, 240, 239),
    "red": (210, 34, 44),
    "green": (65, 173, 74),
    "purple": (154, 64, 152),
    "yellow": (255, 221, 2),
    "dark_green": (2, 106, 59),
    "black": (255, 255, 255),
    "brown": (151, 75, 57),
    "blue": (2, 178, 235),
    "orange": (32, 225, 248),
}

MUTED_OPACITY = 200

print(window.width, window.height)

muted_colors = {
    "white": (238, 240, 239, MUTED_OPACITY),
    "red": (210, 34, 44, MUTED_OPACITY),
    "green": (65, 173, 74, MUTED_OPACITY),
    "purple": (154, 64, 152, MUTED_OPACITY),
    "yellow": (255, 221, 2, MUTED_OPACITY),
    "dark_green": (2, 106, 59, MUTED_OPACITY),
    "black": (255, 255, 255, MUTED_OPACITY),
    "brown": (151, 75, 57, MUTED_OPACITY),
    "blue": (2, 178, 235, MUTED_OPACITY),
    "orange": (32, 225, 248, MUTED_OPACITY),
}

EPSILON = 0

ROD_HEIGHT = 60
ROD_UNIT_WIDTH = 60

BORDER_COLOR = (255, 255, 255)
BACKGROUND_COLOR = (0, 0, 0)
NB_RODS = 10

OFF_SIZE = 40
off_button = shapes.Rectangle(
    x=window.width - OFF_SIZE,
    y=window.height - OFF_SIZE,
    height=OFF_SIZE,
    width=OFF_SIZE,
    color=colors["red"],
)

rods_menu = []
for i, color in enumerate(muted_colors.values()):
    rods_menu.append(
        shapes.BorderedRectangle(
            x=0,
            y=window.height - ROD_HEIGHT * NB_RODS + i * ROD_HEIGHT,
            width=ROD_UNIT_WIDTH * (i + 1),
            height=ROD_HEIGHT,
            color=color,
            border_color=BORDER_COLOR,
            batch=menu_rods_batch,
        )
    )

rods = []

held_rod = None

HAPTIC = False
SIGNAL = None
signals = []
hap2u2 = None

# haptic portion, comment me out when testing on computer
if args.haptic:
    hap2u2 = pyhaptic.Hap2U2()
    hap2u2.clear()
    BASE_PERIOD = 20
    signals = [
        pyhaptic.Signal(pyhaptic.T_SINE, 255, 0, 0, i * BASE_PERIOD, 0) for i in range(NB_RODS)
    ]
    HAPTIC = True

menu_height = NB_RODS * ROD_HEIGHT
menu_width = NB_RODS * ROD_UNIT_WIDTH
menu_border = shapes.BorderedRectangle(
    x=0,
    y=window.height - menu_height,
    width=menu_width,
    height=menu_height,
    border_color=BORDER_COLOR,
    color=BACKGROUND_COLOR,
)


HIDDEN_MENU = False


@window.event
def on_draw():
    global SIGNAL
    window.clear()
    if args.fps:
        fps_display.draw()
    if not HIDDEN_MENU:
        menu_border.draw()
        menu_rods_batch.draw()
    rods_batch.draw()
    off_button.draw()
    # for rod in rods:
    #     rod.draw()
    # if held_rod is not None:
    #     held_rod.draw()


def true_x(rec):
    return rec.x - rec.anchor_x


def true_y(rec):
    return rec.y - rec.anchor_y


def set_true_x(rec, x):
    rec.x = x + rec.anchor_x


def set_true_y(rec, y):
    rec.y = y + rec.anchor_y


def within_rectangle(x, y, rec):
    return true_x(rec) < x < (true_x(rec) + rec.width) and true_y(rec) < y < (
        true_y(rec) + rec.height
    )


def collide(rec1, rec2, epsilon=0):
    return overlap_x(rec1, rec2, epsilon) and overlap_y(rec1, rec2, epsilon)


# rec2 is the moving rec, we are assuming that both recs are colliding
def overlap_top(rec1, rec2, epsilon=0):
    return true_y(rec2) - epsilon <= true_y(rec1) <= true_y(rec2) + rec2.height + epsilon


def overlap_bottom(rec1, rec2, epsilon=0):
    return true_y(rec1) - epsilon <= true_y(rec2) <= true_y(rec1) + rec1.height + epsilon


def overlap_x(rec1, rec2, epsilon=0):
    return overlap_right(rec1, rec2, epsilon) or overlap_left(rec1, rec2, epsilon)


def overlap_y(rec1, rec2, epsilon=0):
    return overlap_top(rec1, rec2, epsilon) or overlap_bottom(rec1, rec2, epsilon)


def overlap_right(rec1, rec2, epsilon=0):
    return true_x(rec2) - epsilon <= true_x(rec1) <= true_x(rec2) + rec2.width + epsilon


def overlap_left(rec1, rec2, epsilon=0):
    return true_x(rec1) - epsilon <= true_x(rec2) <= true_x(rec1) + rec1.width + epsilon


class PositionY(Enum):
    TOP = 1
    BOTTOM = 2


class PositionX(Enum):
    RIGHT = 1
    LEFT = 2


class RelativePosition(Enum):
    COMPLETELY_RIGHT = 1
    COMPLETELY_LEFT = 2
    COMPLETELY_TOP = 3
    COMPLETELY_BOTTOM = 4


def relative_positionX(rec1, rec2, epsilon=0):
    if true_x(rec2) >= true_x(rec1) + rec1.width - epsilon:
        return RelativePosition.COMPLETELY_RIGHT
    if true_x(rec2) + rec2.width <= true_x(rec1) + epsilon:
        return RelativePosition.COMPLETELY_LEFT
    if true_y(rec2) >= true_y(rec1) + rec1.height - epsilon:
        return RelativePosition.COMPLETELY_TOP
    if true_y(rec2) + rec2.height <= true_y(rec1) + epsilon:
        return RelativePosition.COMPLETELY_BOTTOM


@window.event
def on_mouse_press(x, y, button, modifiers):
    global HIDDEN_MENU
    global held_rod
    rod_to_hold = None
    if within_rectangle(x, y, off_button):
        HIDDEN_MENU = not HIDDEN_MENU
    for i, rod in enumerate(rods):
        if within_rectangle(x, y, rod):
            rod_to_hold = i
            break
    if rod_to_hold is not None:
        held_rod = rods.pop(rod_to_hold)
        held_rod.anchor_x = x - held_rod.x
        held_rod.anchor_y = y - held_rod.y
        held_rod.x = x
        held_rod.y = y
        if HAPTIC:
            hap2u2.set_signal(
                pyhaptic.ISOTROPIC,
                pyhaptic.PERMANENT,
                signals[held_rod.width // ROD_UNIT_WIDTH - 1],
            )
    elif not HIDDEN_MENU:
        for i, rod in enumerate(rods_menu):
            if within_rectangle(x, y, rod):
                rod_to_hold = i
                break

        if rod_to_hold is not None:
            target_rod = rods_menu[rod_to_hold]
            r, g, b, _ = target_rod.color
            color = (r, g, b)
            held_rod = shapes.BorderedRectangle(
                x=target_rod.x,
                y=target_rod.y,
                color=color,
                width=target_rod.width,
                height=target_rod.height,
                border_color=BORDER_COLOR,
                batch=rods_batch,
            )
            held_rod.anchor_x = x - held_rod.x
            held_rod.anchor_y = y - held_rod.y
            held_rod.x = x
            held_rod.y = y
            if HAPTIC:
                hap2u2.set_signal(
                    pyhaptic.ISOTROPIC,
                    pyhaptic.PERMANENT,
                    signals[held_rod.width // ROD_UNIT_WIDTH - 1],
                )


@window.event
def on_mouse_release(x, y, button, modifiers):
    global SIGNAL
    if HAPTIC:
        hap2u2.clear()
    global held_rod
    if held_rod is not None:
        old_anchor_x = held_rod.anchor_x
        old_anchor_y = held_rod.anchor_y
        held_rod.anchor_x = 0
        held_rod.anchor_y = 0
        held_rod.x = held_rod.x - old_anchor_x
        held_rod.y = held_rod.y - old_anchor_y
        rods.append(held_rod)
        held_rod = None


blocked_x = False
blocked_y = False


@window.event
def on_mouse_drag(x, y, dx, dy, button, modifiers):
    global held_rod
    global blocked_x
    global blocked_y
    if held_rod is not None:
        old_x = held_rod.x
        old_y = held_rod.y
        old_rod = shapes.Rectangle(
            x=true_x(held_rod), y=true_y(held_rod), width=held_rod.width, height=held_rod.height
        )

        held_rod.x = x
        held_rod.y = y
        still_blocked_x = False
        still_blocked_y = False
        will_be_blocked_x = False
        will_be_blocked_y = False
        colliding_rods = []
        for rod in rods:
            if collide(rod, held_rod, epsilon=0):
                colliding_rods.append(rod)

        for rod in colliding_rods:
            r_pos = relative_positionX(rod, old_rod)
            if r_pos == RelativePosition.COMPLETELY_BOTTOM:
                still_blocked_y = True
                if not blocked_y:
                    set_true_y(held_rod, true_y(rod) - held_rod.height)
                else:
                    held_rod.y = old_y
                will_be_blocked_y = True

            elif r_pos == RelativePosition.COMPLETELY_TOP:
                still_blocked_y = True
                if not blocked_y:
                    set_true_y(held_rod, true_y(rod) + rod.height)
                else:
                    held_rod.y = old_y
                will_be_blocked_y = True

            elif r_pos == RelativePosition.COMPLETELY_LEFT:
                still_blocked_x = True
                if not blocked_x:
                    set_true_x(held_rod, true_x(rod) - held_rod.width)
                else:
                    held_rod.x = old_x
                will_be_blocked_x = True

            elif r_pos == RelativePosition.COMPLETELY_RIGHT:
                still_blocked_x = True
                if not blocked_x:
                    set_true_x(held_rod, true_x(rod) + rod.width)
                else:
                    held_rod.x = old_x
                will_be_blocked_x = True

            else:
                print("wtf?")

        if not still_blocked_x:
            blocked_x = False

        if not still_blocked_y:
            blocked_y = False

        if will_be_blocked_x:
            blocked_x = True
        if will_be_blocked_y:
            blocked_y = True


pyglet.app.run()
