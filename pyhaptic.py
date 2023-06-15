import evdev
import json
import threading
import time
import websockets
from websockets.sync.client import connect

P_SPATIAL   = 0x00
P_TEMPORAL  = 0x80

R_NORMAL    = 0x00
R_REVERT    = 0x40

C_ADD       = 0x00
C_SUB       = 0x10
C_MUL       = 0x20
C_FREQ      = 0x30

ISOTROPIC   = -1
PERMANENT   = -1

T_NONE      = 0x00
T_STEADY    = 0x01
T_SINE      = 0x02
T_TRIANGLE  = 0x03
T_FRONT_TEETH   = 0x04
T_BACK_TEETH    = 0x05
T_CUSTOM0   = 0x08
T_CUSTOM1   = 0x09
T_CUSTOM2   = 0x0A
T_CUSTOM3   = 0x0B
T_CUSTOM4   = 0x0C
T_CUSTOM5   = 0x0D
T_CUSTOM6   = 0x0E
T_CUSTOM7   = 0x0F

TOUCH_START = 0
TOUCH_END   = 1
TOUCH_MOVE  = 2

class Signal:
    def __init__(self, type, amplitude, offset, duty, period, phase) :
        self.type = type
        self.amplitude = amplitude
        self.offset = offset
        self.duty = duty
        self.period = period
        self.phase = phase

class Hap2U2:
    def __init__(self) :
        with connect("ws://localhost:8765") as socket:
            self.socket = socket


        self.device = evdev.InputDevice("/dev/input/event0")
        self.thread = threading.Thread(target=self.pollTouch)
        self.thread.daemon = True
        self.thread.start()

    def set_signal(self, angle, pulses, signal):
        req = {
            "func": "hap2u2_set_signal",
            "args": [angle, pulses, signal.__dict__],
        }

        self.socket.send(json.dumps(req))

    def add_signal(self, angle, pulses, signal) :
        req = {
            "func": "hap2u2_add_signal",
            "args": [angle, pulses, signal.__dict__],
        }

        self.socket.send(json.dumps(req))

    def clear(self) :
        req = {
            "func": "hap2u2_clear",
        }

        self.socket.send(json.dumps(req))

    def on_touch(self, action, x, y, time) :
        req = {
            "func": "hap2u2_on_touch",
            "args": [action, x, y, time],
        }

        self.socket.send(json.dumps(req))

    def pollTouch(self) :
        finger = {
            "x": 0,
            "y": 0,
            "touch": False,
            "first": False,
        }

        for event in self.device.read_loop() :
            if event.code == evdev.ecodes.ABS_MT_POSITION_X :
                finger["x"] = round(event.value * 1024 / 4096)

            if event.code == evdev.ecodes.ABS_MT_POSITION_Y :
                finger["y"] = round(event.value * 600 / 4096)

            if event.code == evdev.ecodes.ABS_MT_TRACKING_ID :
                if event.value > -1 :
                    finger["touch"] = True
                    finger["first"] = True
                else :
                    finger["touch"] = False
                    finger["first"] = True

            if event.code == evdev.ecodes.SYN_REPORT :
                if finger["touch"] :
                    if finger["first"] :
                        self.on_touch(TOUCH_START, finger["x"], finger["y"], time.time())
                        finger["first"] = False
                    else :
                        self.on_touch(TOUCH_MOVE, finger["x"], finger["y"], time.time())
                else :
                    if finger["first"] :
                        self.on_touch(TOUCH_END, finger["x"], finger["y"], time.time())
                        finger["first"] = False


