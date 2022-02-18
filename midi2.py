#!/usr/bin/env python
from pygame import midi
import time
import os

"""
this code is for a custom midi device that my brother made
here's a video of the wiring process: https://www.youtube.com/watch?v=jEtFtwcCJcM

reference for the device's code:
https://learn.adafruit.com/grand-central-usb-midi-controller-in-circuitpython/code-usb-midi-in-circuitpython

references I used to make this code:
https://stackoverflow.com/questions/1554896/getting-input-from-midi-devices-live-python
https://www.pygame.org/docs/ref/midi.html
"""

midi.init()
print(midi.get_count())
for id in range(midi.get_count()):
  interf, name, is_input, is_output, is_opened = midi.get_device_info(id)
  #s = "id: {}".format(id)
  s = interf.decode("utf-8") + " " + name.decode("utf-8")
  if is_input == 1:
    s += " input"
  if is_output == 1:
    s += " output"
  if is_opened == 1:
    s += " (opened)"
  print(id, s)

#input_id = midi.get_default_input_id()
#input_id = 5
print("Enter the number above corresponding to the input of the mixer device")
input_id = int(input())
input_device = midi.Input(input_id)

#output_id = midi.get_default_input_id()
#output_id = 4
print("Enter the number above corresponding to the output of the mixer device")
output_id = int(input())
output_device = midi.Output(output_id)

output_device.note_off(1)
output_device.note_off(2)
output_device.note_off(3)
output_device.note_off(4)
output_device.note_off(5)

def process_data(isButton, channel, value):
  if isButton:
    if value:
      print("button {} pressed".format(channel))
      output_device.note_on(channel+1, 100)
      os.system("/home/user/nextcloud/bin/m-keys {} &".format(channel+1))
    else:
      print("button {} released".format(channel))
      output_device.note_off(channel+1)
  else: #isButton = false, it is a slider
    print("slider {} value: {}".format(channel, value))



while True:
  while not input_device.poll():
    time.sleep(0.05)
  data = input_device.read(1)
  print(data[0][0])
  button_or_slider, channel, value, _ = data[0][0]
  if button_or_slider == 176: #slider value
    process_data(False, channel, value)
  elif button_or_slider == 144: #button pressed
    process_data(True, channel, True)
  elif button_or_slider == 128: #button released
    process_data(True, channel, False)

#[[[176, 4, 79, 0], 0]] slider 4 value: 79
#[[[144, 3, 127, 0], 0]] button 3 pressed
#[[[128, 3, 127, 0], 1]] button 3 released

