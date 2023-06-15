import copy
from enum import Enum

import pyglet
from pyglet import shapes

window = pyglet.window.Window(fullscreen=True)

colors = {"white": (238, 240, 239), "red": (210, 34, 44), "green": (65, 173, 74),
          "purple": (154, 64, 152), "yellow": (255, 221, 2), "dark_green": (2, 106, 59),
          "black": (255, 255, 255), "brown": (151, 75, 57), "blue": (2, 178, 235), "orange": (32, 225, 248)}

MUTED_OPACITY = 200

muted_colors = {"white": (238, 240, 239, MUTED_OPACITY), "red": (210, 34, 44, MUTED_OPACITY), "green": (65, 173, 74, MUTED_OPACITY),
          "purple": (154, 64, 152, MUTED_OPACITY), "yellow": (255, 221, 2, MUTED_OPACITY), "dark_green": (2, 106, 59, MUTED_OPACITY),
          "black": (255, 255, 255, MUTED_OPACITY), "brown": (151, 75, 57, MUTED_OPACITY), "blue": (2, 178, 235, MUTED_OPACITY), "orange": (32, 225, 248, MUTED_OPACITY)}

EPSILON = 0

ROD_HEIGHT = 20
ROD_UNIT_WIDTH = 40

rods_menu = []
for i, color in enumerate(muted_colors.values()):
    rods_menu.append(
        shapes.Rectangle(x=0, y=(i + 1) * ROD_HEIGHT, width=ROD_UNIT_WIDTH * (i + 1), height=ROD_HEIGHT,
                         color=color))

rods = []

held_rod = None

@window.event
def on_draw():
    window.clear()
    for rod in rods_menu:
        rod.draw()
    for rod in rods:
        rod.draw()
    if held_rod is not None:
        held_rod.draw()


def true_x(rec):
    return rec.x - rec.anchor_x


def true_y(rec):
    return rec.y - rec.anchor_y


def set_true_x(rec, x):
    rec.x = x + rec.anchor_x


def set_true_y(rec, y):
    rec.y = y + rec.anchor_y


def within_rectangle(x, y, rec):
    return true_x(rec) < x < (true_x(rec) + rec.width) and true_y(rec) < y < (true_y(rec) + rec.height)


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
    global held_rod
    rod_to_hold = None
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
    else:
        for i, rod in enumerate(rods_menu):
            if within_rectangle(x, y, rod):
                rod_to_hold = i
                break

        if rod_to_hold is not None:
            target_rod = rods_menu[rod_to_hold]
            r,g,b,_ = target_rod.color
            color = (r,g,b)
            held_rod = shapes.Rectangle(x=target_rod.x, y=target_rod.y, color=color, width=target_rod.width, height=target_rod.height)
            held_rod.anchor_x = x - held_rod.x
            held_rod.anchor_y = y - held_rod.y
            held_rod.x = x
            held_rod.y = y


@window.event
def on_mouse_release(x, y, button, modifiers):
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
        old_rod = shapes.Rectangle(x=true_x(held_rod), y=true_y(held_rod), width=held_rod.width, height=held_rod.height)

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
