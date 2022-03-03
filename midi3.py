#!/usr/bin/env python
from pygame import midi
import time
import pulsectl
#note: could try pulsectl_asyncio
from pyudev import Context, Monitor

"""
this code is for a custom midi device that my brother made
here's a video of the wiring process: https://www.youtube.com/watch?v=jEtFtwcCJcM

reference for the device's code:
https://learn.adafruit.com/grand-central-usb-midi-controller-in-circuitpython/code-usb-midi-in-circuitpython

references I used to make this code:
https://stackoverflow.com/questions/1554896/getting-input-from-midi-devices-live-python
https://www.pygame.org/docs/ref/midi.html
https://pypi.org/project/pulsectl/
https://stackoverflow.com/questions/51007632/how-to-monitor-usb-devices-insertion#51011386

"""

RAISE_MAX_VOLUME = False
IGNORE_SORCE_MONITORS = True
VERBOSE = False

class MidiMixer:
  def __init__(self, midi_device_name="QT Py M0 MIDI 1", num_channels=5):
    self.midi_device_name = midi_device_name
    self.num_channels = num_channels

    context = Context()
    self.monitor = Monitor.from_netlink(context)
    self.monitor.filter_by(subsystem='usb', device_type='usb_device')

    self.wait_for_midi_device()

  def find_midi_device(self):
    self.input_device = None
    self.output_device = None
    self.buttons = [False] * self.num_channels
    self.sliders = [None] * self.num_channels
    self.leds = [None] * self.num_channels

    midi.quit()
    midi.init()
    all_midi_device_names = set()
    for id in range(midi.get_count()):
      interf, name, is_input, is_output, is_opened = midi.get_device_info(id)
      name = name.decode("utf-8")
      all_midi_device_names.add(name)
      if name == self.midi_device_name:
        if is_input == 1:
          print("input id {} found for '{}'".format(id, name))
          self.input_device = midi.Input(id)
        if is_output == 1:
          print("output id {} found for '{}'".format(id, name))
          self.output_device = midi.Output(id)
    print("all midi devices:", all_midi_device_names)
    return not (self.input_device is None or self.output_device is None)

  def wait_for_midi_device(self):
    # midi.quit()
    while not self.find_midi_device():
      device = None
      while device is None:
        device = self.monitor.poll(timeout=1)
        if device is not None and device.properties["ACTION"] != "add":
          device = None
      print("usb device plugged in, trying to connect...")
      # midi.quit()

  def set_led(self, channel, value=True, force=False):
    if self.leds[channel] != value or force:
      if VERBOSE: print("led {} => {}".format(channel, value))
      self.leds[channel] = value
      try:
        if value:
          self.output_device.note_on(channel+1, 100)
        else:
          self.output_device.note_off(channel+1)
      except Exception as e:
        if e.args[0] == b"PortMidi: `Host error'": #only resolve a midi connection error
          print("device unplugged, waiting for reconnect...")
          self.input_device.close()
          self.output_device.close()
          self.wait_for_midi_device()
        else:
          raise e

  def check_for_unplug(self):
    device = self.monitor.poll(timeout=0) #non-blocking
    if device is not None and device.properties["ACTION"] == "remove":
      print("usb device unplugged, checking if mixer still plugged in")
      #force setting an LED to the same value to test if still connected
      self.set_led(0, self.leds[0], force=True)
      return True
    return False

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
    self.connect()

  def connect(self, tries=5):
    for i in range(tries):
      try:
        self.pulse = pulsectl.Pulse(self.name) #this may fail
        
        #possible event masks:
        #null sink source sink-input source-output module client sample-cache server autoload card all
        self.pulse.event_mask_set("sink", "source", "sink-input")
        # self.pulse.event_mask_set("all")
        self.pulse.event_callback_set(self.pulse_callback)
        self.pending_event = True
        print("successfully connected to pulse")
        return
      except pulsectl.pulsectl.PulseError as e:
        print("error connecting to pulse, retrying...")
        time.sleep(0.1)
        if i == tries-1:
          raise e

  def pulse_callback(self, event):
    # if VERBOSE: print(event)
    self.pending_event = True

  def wait_and_listen(self, timeout):
    try:
      self.pulse.event_listen(timeout=timeout)
    except pulsectl.pulsectl.PulseDisconnected as e:
      print("pulseaudio disconnected, reconnecting")
      self.connect()
    result = self.pending_event
    self.pending_event = False
    return result

  def refresh_volume_controls(self):
    try:
      sink_list = self.pulse.sink_list()
      source_list = self.pulse.source_list()
      sink_input_list = self.pulse.sink_input_list()

      if IGNORE_SORCE_MONITORS:
        source_list = [x for x in source_list if not "monitor" in x.name]

      self.volume_controls = sink_list + source_list + sink_input_list
    except pulsectl.pulsectl.PulseOperationFailed as e:
      print(e)

  def set_volume(self, channel, value):
    if channel < len(self.volume_controls):
      try:
        self.pulse.volume_set_all_chans(self.volume_controls[channel], value)
      except pulsectl.pulsectl.PulseOperationFailed as e:
      # time.sleep(1) #TODO retry instead of sleeping before 1st try
        print(e)
      if VERBOSE: print("channel {} volume set to {}".format(channel, value))
    else:
      if VERBOSE: print("set_volume of channel {} ignored, nothing to control".format(channel))

  def toggle_mute(self, channel):
    if channel < len(self.volume_controls):
      volume_control = self.volume_controls[channel]
      if VERBOSE: print("toggle mute for:", volume_control)
      try:
        self.pulse.mute(volume_control, not volume_control.mute)
      except pulsectl.pulsectl.PulseOperationFailed as e:
        print(e)
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



mixer = MidiMixer()
volctl = VolumeController()

while True:
  events = []
  while not events:
    events = mixer.poll()
    if volctl.wait_and_listen(0.01) or mixer.check_for_unplug():
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
