# ////////////////////////////////////////////////////////////////
# //                     IMPORT STATEMENTS                      //
# ////////////////////////////////////////////////////////////////

import math
import sys
import time
import threading

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import *
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.animation import Animation
from functools import partial
from kivy.config import Config
from kivy.core.window import Window
from pidev.kivy import DPEAButton
from pidev.kivy import PauseScreen
from time import sleep
import RPi.GPIO as GPIO
from pidev.stepper import stepper
from pidev.Cyprus_Commands import Cyprus_Commands_RPi as cyprus

# ////////////////////////////////////////////////////////////////
# //                      GLOBAL VARIABLES                      //
# //                         CONSTANTS                          //
# ////////////////////////////////////////////////////////////////
ON = False
OFF = True
HOME = True
TOP = False
OPEN = False
CLOSE = True
YELLOW = .180, 0.188, 0.980, 1
BLUE = 0.917, 0.796, 0.380, 1
DEBOUNCE = 0.1
INIT_RAMP_SPEED = 2
RAMP_LENGTH = 725


# ////////////////////////////////////////////////////////////////
# //            DECLARE APP CLASS AND SCREENMANAGER             //
# //                     LOAD KIVY FILE                         //
# ////////////////////////////////////////////////////////////////
class MyApp(App):
    def build(self):
        self.title = "Perpetual Motion"
        return sm


Builder.load_file('main.kv')
Window.clearcolor = (.1, .1, .1, 1)  # (WHITE)

cyprus.open_spi()

# ////////////////////////////////////////////////////////////////
# //                    SLUSH/HARDWARE SETUP                    //
# ////////////////////////////////////////////////////////////////
sm = ScreenManager()
ramp = stepper(port=0, micro_steps=32, hold_current=20, run_current=20, accel_current=20, deaccel_current=20,
               steps_per_unit=200, speed=4)

ramp.set_max_speed(6)


# ////////////////////////////////////////////////////////////////
# //                       MAIN FUNCTIONS                       //
# //             SHOULD INTERACT DIRECTLY WITH HARDWARE         //
# ////////////////////////////////////////////////////////////////
# ////////////////////////////////////////////////////////////////
# //        DEFINE MAINSCREEN CLASS THAT KIVY RECOGNIZES        //
# //                                                            //
# //   KIVY UI CAN INTERACT DIRECTLY W/ THE FUNCTIONS DEFINED   //
# //     CORRESPONDS TO BUTTON/SLIDER/WIDGET "on_release"       //
# //                                                            //
# //   SHOULD REFERENCE MAIN FUNCTIONS WITHIN THESE FUNCTIONS   //
# //      SHOULD NOT INTERACT DIRECTLY WITH THE HARDWARE        //
# ////////////////////////////////////////////////////////////////

class MainScreen(Screen):
    version = cyprus.read_firmware_version()
    staircaseSpeedText = '0'
    staircaseSpeed = 40

    """Servo gate variables"""
    gate_pos = 0
    servo_open = 0.35
    servo_closed = 0.15

    """Ramp toggle variables"""
    stair_state = 0  # ramp starts off
    ramp_sens_lower_state = 2
    ramp_sens_upper_state = 2

    def __init__(self, **kwargs):

        """Things that happen at the initializing of the Main Screen"""

        super(MainScreen, self).__init__(**kwargs)

        Clock.schedule_interval(self.variables, 1)
        cyprus.set_servo_position(2, self.servo_closed)
        cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)

    def variables(self, dt):

        """giving real time feedback through a singular clock object that prints to the station and informs the user
        where the ball currently lies"""

        if cyprus.read_gpio() & 0b0010:  # sensor returns this if there is nothing at the bottom of the ramp
            self.ramp_sens_lower_state = 0
            print("lower_state " + str(self.ramp_sens_lower_state))

            self.ids.ball_ready.text = "Ball is not at bottom of ramp"  # updates label

        else:
            self.ramp_sens_lower_state = 1
            print("lower_state " + str(self.ramp_sens_lower_state))

            self.ids.ball_ready.text = "Ready to start!"  # updates label

        if cyprus.read_gpio() & 0b0001:
            self.ramp_sens_upper_state = 0
            print("upper_state " + str(self.ramp_sens_upper_state))

        else:
            self.ramp_sens_upper_state = 1
            print("upper_state " + str(self.ramp_sens_upper_state))

    def toggleGate(self):

        """Opens and closes the gate. Uses a "gate_pos" variable to find out the gate's state"""

        if self.gate_pos == 0:
            cyprus.set_servo_position(2, self.servo_open)
            self.gate_pos = 1

        else:
            cyprus.set_servo_position(2, self.servo_closed)
            self.gate_pos = 0

    def toggleStaircase(self):

        """Toggles the staircase on and off. The PMW value is controlled by the Kivy UI"""

        if self.stair_state == 0:
            cyprus.set_pwm_values(1, period_value=100000, compare_value=self.ids.staircaseSpeed.value,
                                  compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            self.stair_state = 1

        else:
            cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            self.stair_state = 0

    def rampUp(self):

        """Tells ramp to move a full length upwards... not good for the machine if it starts at the top!!"""

        if self.ramp_sens_upper_state == 1:
            print("Don't press Ramp UP when the ball is here!")

        else:
            sleep(.1)
            ramp.softStop()
            ramp.start_relative_move(28.5)
            print("ramp is going up!")

    def rampDown(self):

        """Tells ramp to move a full length downwards... not good for the machine if it starts at the bottom!!"""

        if self.ramp_sens_lower_state == 1:
            print("Don't press Ramp DOWN when the ball is here!")

        else:
            ramp.start_relative_move(-28.5)
            print("ramp is going down!")

    def auto(self):

        """Goes through one cycle of the machine. Will only work if the ball and ramp are at the lower position"""

        print("Run through one cycle of the perpetual motion machine")

        ramp.set_as_home()

        if self.ramp_sens_lower_state == 1:

            ramp.set_speed(2)
            cyprus.set_servo_position(2, self.servo_closed)
            sleep(.5)
            ramp.start_relative_move(28.5)

            sleep(14)

            ramp.softStop()
            ramp.goHome()

            cyprus.set_pwm_values(1, period_value=100000, compare_value=self.ids.staircaseSpeed.value,
                                  compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            sleep(15)
            cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)

            cyprus.set_servo_position(2, self.servo_open)
            sleep(1)
            cyprus.set_servo_position(2, self.servo_closed)

        else:

            print("move ball to bottom of ramp to start")

    def setRampSpeed(self, speed):

        """Sets the ramp speed"""

        if not ramp.is_busy():
            ramp.set_speed(self.ids.rampSpeed.value * .02)
            ramp_check = self.ids.rampSpeed.value * .02
            print("ramp speed is " + str(ramp_check))

        else:

            print("wait for ramp to finish!")

    def setStaircaseSpeed(self, speed):

        """Updates the staircase speed only if it is on."""

        if self.stair_state == 1:
            cyprus.set_pwm_values(1, period_value=100000, compare_value=self.ids.staircaseSpeed.value,
                                  compare_mode=cyprus.LESS_THAN_OR_EQUAL)

    def resetColors(self):
        self.ids.gate.color = YELLOW
        self.ids.staircase.color = YELLOW
        self.ids.ramp.color = YELLOW
        self.ids.auto.color = BLUE

    def quit(self):

        """Quit function. Servo motor often has a mind of its own :("""

        ramp.free_all()
        sleep(.5)
        cyprus.set_servo_position(2, .15)
        cyprus.sleep(.5)
        cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
        cyprus.sleep(.5)
        cyprus.close()
        GPIO.cleanup()
        print("Exit")
        MyApp().stop()


sm.add_widget(MainScreen(name='main'))

# ////////////////////////////////////////////////////////////////
# //                          RUN APP                           //
# ////////////////////////////////////////////////////////////////

MyApp().run()
cyprus.close_spi()
