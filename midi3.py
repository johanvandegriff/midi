#!/usr/bin/env python
# import pygame
from pygame import midi
import time
import os
import pulsectl
#note: could try pulsectl_asyncio

"""
this code is for a custom midi device that my brother made
here's a video of the wiring process: https://www.youtube.com/watch?v=jEtFtwcCJcM

reference for the device's code:
https://learn.adafruit.com/grand-central-usb-midi-controller-in-circuitpython/code-usb-midi-in-circuitpython

references I used to make this code:
https://stackoverflow.com/questions/1554896/getting-input-from-midi-devices-live-python
https://www.pygame.org/docs/ref/midi.html
https://pypi.org/project/pulsectl/
"""

device_name = "QT Py M0 MIDI 1"
verbose = True

midi.init()
# print(midi.get_count())
input_id = None
output_id = None

for id in range(midi.get_count()):
  interf, name, is_input, is_output, is_opened = midi.get_device_info(id)
  name = name.decode("utf-8")
  if name == device_name:
    if is_input == 1:
      print("found input device for " + name)
      input_id = id
    if is_output == 1:
      print("found output device for " + name)
      output_id = id

#input_id = midi.get_default_input_id()
#input_id = 5
# print("Enter the number above corresponding to the input of the mixer device")
# input_id = int(input())
input_device = midi.Input(input_id)

#output_id = midi.get_default_input_id()
#output_id = 4
# print("Enter the number above corresponding to the output of the mixer device")
# output_id = int(input())
output_device = midi.Output(output_id)

# output_device.note_off(1)
# output_device.note_off(2)
# output_device.note_off(3)
# output_device.note_off(4)
# output_device.note_off(5)

pulse = pulsectl.Pulse('my-client-name')

def get_volume_controls():
  volume_controls = pulse.sink_list() + [x for x in pulse.source_list() if not "monitor" in x.name] + pulse.sink_input_list()
  #volume_controls = pulse.sink_input_list()
  return volume_controls

def process_data(isButton, channel, value):
  volume_controls = get_volume_controls() #TODO move this out to avoid duplication
  if channel >= len(volume_controls):
    if verbose: print("event on channel {} ignored because no volume control is attached".format(channel))
  else:
    volume_control = volume_controls[channel]
    if isButton:
      if value:
        if verbose: print("button {} pressed".format(channel))
        #output_device.note_on(channel+1, 100)
        pulse.mute(volume_control, not volume_control.mute)
        update_mute_light(channel, volume_control, verbose)
        #os.system("pactl set-sink-mute @DEFAULT_SINK@ toggle #{}".format(channel+1))
      else:
        if verbose: print("button {} released".format(channel))
        #output_device.note_off(channel+1)
    else: #isButton = false, it is a slider
      scaled = value / 127.0
      if verbose: print("slider {} value: {} scaled: {}".format(channel, value, scaled))
      pulse.volume_set_all_chans(volume_control, scaled)
      #os.system("pactl set-sink-volume @DEFAULT_SINK@ {}%".format(scaled))

# Initializing Pygame
#pygame.init()

# Initializing surface
#surface = pygame.display.set_mode((400,300))

# Initialing Color
#color = (255,0,0)

# Drawing Rectangle
#pygame.draw.rect(surface, color, pygame.Rect(30, 30, 60, 60))
#pygame.display.flip()

pending_event = False

def handle_events(ev):
  global pending_event
  pending_event = True
  # print(pending_event)
  # print('Pulse event:', ev)

pulse.event_mask_set('all')
pulse.event_callback_set(handle_events)
## pulse.event_listen(timeout=10)

def update_mute_light(channel, volume_control, verbose):
  if volume_control.mute:
    if verbose: print("channel {} muted (/)".format(channel))
    output_device.note_off(channel+1)
  else:
    if verbose: print("channel {} unmuted (o)".format(channel))
    output_device.note_on(channel+1, 100)


def update_mute_lights():
  volume_controls = get_volume_controls()
  for channel, volume_control in enumerate(volume_controls):
    update_mute_light(channel, volume_control, False)
  for channel in range(len(volume_controls),5):
    output_device.note_off(channel+1)

update_mute_lights()
while True:
  while not input_device.poll():
    pulse.event_listen(timeout=0.05)
    # time.sleep(0.05)
    # update_mute_lights()
    # print(pending_event)
    if pending_event:
      if verbose: print("callback returned event, refreshing LEDs")
      #TODO ignore callback events generated from itself if possible, maybe disable and re-enable callback, maybe its ok
      pending_event = False
      update_mute_lights()
  # print(input_device.read(999))
  # print()
  #TODO only use the last event of each type (slider, button) from each channel
  for data in input_device.read(10):
    if verbose: print(data[0])
    button_or_slider, channel, value, _ = data[0]
    if button_or_slider == 176: #slider value
      process_data(False, channel, value)
    elif button_or_slider == 144: #button pressed
      process_data(True, channel, True)
    elif button_or_slider == 128: #button released
      process_data(True, channel, False)

#[[[176, 4, 79, 0], 0]] slider 4 value: 79
#[[[144, 3, 127, 0], 0]] button 3 pressed
#[[[128, 3, 127, 0], 1]] button 3 released

