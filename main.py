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
               steps_per_unit=200, speed=2)

ramp.set_max_speed(4)


# ////////////////////////////////////////////////////////////////
# //                       MAIN FUNCTIONS                       //
# //             SHOULD INTERACT DIRECTLY WITH HARDWARE         //
# ////////////////////////////////////////////////////////////////
class Functions:

    def panic(self):
        """Does everything the same as the quit function but more aggressively."""

        ramp.softStop()
        cyprus.set_servo_position(2, self.servo_closed)
        sleep(.1)
        cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
        cyprus.close()
        GPIO.cleanup()
        print("PANIC!")
        MyApp().stop()


# ////////////////////////////////////////////////////////////////
# //        DEFINE MAINSCREEN CLASS THAT KIVY RECOGNIZES        //
# //                                                            //
# //   KIVY UI CAN INTERACT DIRECTLY W/ THE FUNCTIONS DEFINED   //
# //     CORRESPONDS TO BUTTON/SLIDER/WIDGET "on_release"       //
# //                                                            //
# //   SHOULD REFERENCE MAIN FUNCTIONS WITHIN THESE FUNCTIONS   //
# //      SHOULD NOT INTERACT DIRECTLY WITH THE HARDWARE        //
# ////////////////////////////////////////////////////////////////


"""Global variables area"""


class MainScreen(Screen, Functions):
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

        """Creating variables with only one clock function. This should take less processing power than running
        a million clocks"""

        if cyprus.read_gpio() & 0b0010:  # binary bitwise AND of the value returned from read.gpio()
            self.ramp_sens_lower_state = 0
            print("lower_state " + str(self.ramp_sens_lower_state))

            self.ids.ball_ready.text = "Ball is not at bottom of ramp"

        else:
            self.ramp_sens_lower_state = 1
            print("lower_state " + str(self.ramp_sens_lower_state))

            self.ids.ball_ready.text = "Ready to start!"

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

    def rampDown(self):

        """Function to toggle the ramp. Only works if the ball is at the lower sensor and the state is 1"""

        if self.ramp_sens_lower_state == 1:
            print("Don't press Ramp DOWN when the ball is here!")

        else:
            ramp.start_relative_move(-28.5)
            print("ramp is going down!")

    def auto(self):

        """Goes through the machine automatically. Will only work if the ball and ramp are at the lower position"""

        print(ramp.get_position_in_units())
        print("Run through one cycle of the perpetual motion machine")

        if self.ramp_sens_lower_state == 1:

            ramp.set_speed(2)
            cyprus.set_servo_position(2, self.servo_closed)
            sleep(.1)
            ramp.start_relative_move(28.5)

            sleep(16)

            sleep(.1)
            ramp.softStop()
            ramp.goHome()

            cyprus.set_pwm_values(1, period_value=100000, compare_value=self.ids.staircaseSpeed.value,
                                  compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            sleep(15)
            cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)

            cyprus.set_servo_position(2, self.servo_open)
            sleep(2)
            cyprus.set_servo_position(2, self.servo_closed)

        else:

            print("please move ball to bottom of ramp to start")

    def setRampSpeed(self, speed):

        """Sets the ramp speed. The speed variable in the function definition is not used as it wasn't necessary
        but was included in the example."""

        if not ramp.is_busy():
            ramp.set_speed(self.ids.rampSpeed.value * .02)
            ramp_check = self.ids.rampSpeed.value * .02
            print("ramp speed is " + str(ramp_check))

        else:

            print("ramp is busy, leave it be!")

    def setStaircaseSpeed(self, speed):

        """Updates the staircase speed only if it is on."""

        if self.stair_state == 1:
            cyprus.set_pwm_values(1, period_value=100000, compare_value=self.ids.staircaseSpeed.value,
                                  compare_mode=cyprus.LESS_THAN_OR_EQUAL)

    def rampUp(self):

        """Tells the ramp to go home. This doesn't usually work as the ramp needs to be at home when turning it on
        and if it is not at home when the program is initialized then it will not go home and needs to be reset"""

        if self.ramp_sens_upper_state == 1:
            print("Don't press Ramp UP when the ball is here!")

        else:
            sleep(.1)
            ramp.softStop()
            ramp.start_relative_move(28.5)
            print("ramp is going up!")


    def resetColors(self):
        self.ids.gate.color = YELLOW
        self.ids.staircase.color = YELLOW
        self.ids.ramp.color = YELLOW
        self.ids.auto.color = BLUE

    def quit(self):

        """Quit function. This is supposed to put all the components back to their "natural state" but half the time
        it doesn't actually work and the servo does what it wants."""

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

    def PANIC(self):

        """Calls the panic function"""

        self.panic()


sm.add_widget(MainScreen(name='main'))

# ////////////////////////////////////////////////////////////////
# //                          RUN APP                           //
# ////////////////////////////////////////////////////////////////

MyApp().run()
cyprus.close_spi()
