#!/usr/bin/env python
from pygame import midi
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

RAISE_MAX_VOLUME = False
VERBOSE = True

class MidiMixer:
  def __init__(self, midi_device_name="QT Py M0 MIDI 1", num_channels=5):
    self.num_channels = num_channels
    self.midi_device_name = midi_device_name
    self.input_device = None
    self.output_device = None
    self.buttons = [False] * self.num_channels
    self.sliders = [None] * self.num_channels
    self.leds = [None] * self.num_channels
    all_midi_device_names = set()
    for id in range(midi.get_count()):
      interf, name, is_input, is_output, is_opened = midi.get_device_info(id)
      name = name.decode("utf-8")
      all_midi_device_names.add(name)
      if name == midi_device_name:
        if is_input == 1:
          print("found input device for " + name)
          input_id = id
          self.input_device = midi.Input(input_id)
        if is_output == 1:
          print("found output device for " + name)
          output_id = id
          self.output_device = midi.Output(output_id)
    if self.input_device is None or self.output_device is None:
      raise Exception("MIDI device '{}' not found! Device list:\n".format(midi_device_name) + "\n".join(all_midi_device_names))

  def set_led(self, channel, value=True):
    if self.leds[channel] != value:
      if VERBOSE: print("led {} => {}".format(channel, value))
      self.leds[channel] = value
      if value:
        self.output_device.note_on(channel+1, 100)
      else:
        self.output_device.note_off(channel+1)

  def poll(self, read_amount=10):
    events = []
    if self.input_device.poll():
      sliders_old = self.sliders[:]
      buttons_old = self.buttons[:]
      for data in self.input_device.read(read_amount):
        # if VERBOSE: print(data[0])
        button_or_slider, channel, value, _ = data[0]
        if button_or_slider == 176: #slider value
          self.sliders[channel] = value
        elif button_or_slider == 144: #button pressed
          self.buttons[channel] = True
        elif button_or_slider == 128: #button released
          self.buttons[channel] = False
      for channel in range(self.num_channels):
        if sliders_old[channel] != self.sliders[channel]:
          events.append(["slider", channel, self.sliders[channel]])
        if buttons_old[channel] != self.buttons[channel]:
          events.append(["button", channel, self.buttons[channel]])
    return events


class VolumeController:
  def __init__(self, name="volume-controller"): #client name can be whatever
    self.name = name
    self.pulse = pulsectl.Pulse(self.name)
    
    #possible event masks:
    #null sink source sink-input source-output module client sample-cache server autoload card all
    self.pulse.event_mask_set("sink", "source", "sink-input")
    # self.pulse.event_mask_set("all")
    self.pulse.event_callback_set(self.pulse_callback)
    self.pending_event = True

  def pulse_callback(self, event):
    # if VERBOSE: print(event)
    self.pending_event = True

  def wait_and_listen(self, timeout):
    self.pulse.event_listen(timeout=timeout)
    result = self.pending_event
    self.pending_event = False
    return result

  def refresh_volume_controls(self):
    self.volume_controls = self.pulse.sink_list() + [x for x in self.pulse.source_list() if not "monitor" in x.name] + self.pulse.sink_input_list()

  def set_volume(self, channel, value):
    if channel < len(self.volume_controls):
      self.pulse.volume_set_all_chans(self.volume_controls[channel], value)
      if VERBOSE: print("channel {} volume set to {}".format(channel, value))
    else:
      if VERBOSE: print("set_volume of channel {} ignored, nothing to control".format(channel))

  def toggle_mute(self, channel):
    if channel < len(self.volume_controls):
      volume_control = self.volume_controls[channel]
      self.pulse.mute(volume_control, not volume_control.mute)
      if volume_control.mute:
        if VERBOSE: print("channel {} muted (/)".format(channel))
      else:
        if VERBOSE: print("channel {} unmuted (o)".format(channel))
    else:
      if VERBOSE: print("toggle_mute channel {} ignored, nothing to control".format(channel))

  def is_muted(self, channel):
    self.refresh_volume_controls()
    if channel < len(self.volume_controls):
      return self.volume_controls[channel].mute
    else:
      return None



midi.init()
mixer = MidiMixer()
volctl = VolumeController()

while True:
  events = []
  while not events:
    events = mixer.poll()
    if volctl.wait_and_listen(0.01):
      if VERBOSE: print("event detected, refreshing LEDs")
      for channel in range(mixer.num_channels):
        is_muted = volctl.is_muted(channel)
        if is_muted is None: is_muted = True
        mixer.set_led(channel, not is_muted)
  
  volctl.refresh_volume_controls()
  for event_type, channel, value in events:
    if event_type == "button":
      if VERBOSE: print("button {} => {}".format(channel, value))
      if value:
        volctl.toggle_mute(channel)
    elif event_type == "slider":
      scaled = value / 127.0
      if RAISE_MAX_VOLUME:
        scaled = scaled * 1.5
      if VERBOSE: print("slider {} => {} (scaled = {})".format(channel, value, scaled))
      volctl.set_volume(channel, scaled)
