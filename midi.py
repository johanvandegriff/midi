#!/usr/bin/env python
from pygame import midi
import time
import os


"""
this code is for reading a generic midi keyboard

references I used to make this code:
https://stackoverflow.com/questions/1554896/getting-input-from-midi-devices-live-python
https://www.pygame.org/docs/ref/midi.html
https://stackoverflow.com/questions/64818410/pygame-read-midi-input
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

print("Enter the number above corresponding to the input you want to monitor")
input_id = int(input())
input_device = midi.Input(input_id)

while True:
  while not input_device.poll():
    time.sleep(0.05)
  data = input_device.read(1)
#  print(data)
  print(data[0][0])
  event_type, channel, value, _ = data[0][0]
  if event_type == 144: #button pressed
      print("button {} pressed, velocity: {}".format(channel, value))
  elif event_type == 128: #button released
    print("button {} released".format(channel))

