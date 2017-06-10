# -*- coding:utf-8 -*-
#!/usr/bin/python
import pyaudio
import threading
import time
import copy

class AudioIo(threading.Thread):
  def __init__(self, input, rate, input_idx, blocking, buffer_num = 8):
    super(AudioIo, self).__init__()
    self.setDaemon(True)
    self.buffer_num = buffer_num
    self.p=pyaudio.PyAudio()
    self.CHUNK=1024
    self.RATE=rate
    self.input = input
    self.buf = [0] * self.buffer_num
    self.p=pyaudio.PyAudio()
    self.wr_idx = 0
    self.rd_idx = 0
    self.buffering = 0
    self.read_buf = ''
    self.lock = threading.Lock()
    self.debug = False
    self.input_idx = input_idx
    self.blocking = blocking
    self.at_first = False
    self.term = False
    self.started = False
    self.stream_on = False

    def stream_cb( in_data, frame_count, time_info, status ):
#     print (self.log_prefix + 'stream cb!')
      if (self.at_first):
        print (self.log_prefix + 'stream cb before start!')
        return (None, pyaudio.paAbort)
      if (self.input == True):
        ret = self.write_buffer(in_data)
        return (None, pyaudio.paContinue)
      else:
        ret, data = self.read_buffer()
        timeout = 0
        while (ret == False):
          if (self.debug == True):
            print (self.log_prefix + '%d msec sleep! idx : ' % (self.buffer_num * 50), self.rd_idx)

          time.sleep((self.buffer_num * 50) / 1000.000)
          timeout += 1
          if (timeout > 10):
            print (self.log_prefix + 'time out!')
            break;

          ret, data = self.read_buffer()

        return (data, pyaudio.paContinue)

    self.at_first = True
    if (self.blocking == True):
      if (self.input == True):
        self.log_prefix = '[IN]  : '
        self.stream=self.p.open(  format = pyaudio.paInt16,
                        channels = 1,
                        rate = self.RATE,
                        frames_per_buffer = self.CHUNK,
                        input = True,
                        input_device_index = self.input_idx) 
      else:
        self.log_prefix = '[OUT] : '
        self.stream=self.p.open(  format = pyaudio.paInt16,
                        channels = 1,
                        rate = self.RATE,
                        frames_per_buffer = self.CHUNK,
                        output = True)
    else:
      if (self.input == True):
        self.log_prefix = '[IN]  : '
        self.stream=self.p.open(  format = pyaudio.paInt16,
                        channels = 1,
                        rate = self.RATE,
                        frames_per_buffer = self.CHUNK,
                        input = True,
                        input_device_index = self.input_idx,
                        stream_callback=stream_cb) 
      else:
        self.log_prefix = '[OUT] : '
        self.stream=self.p.open(  format = pyaudio.paInt16,
                        channels = 1,
                        rate = self.RATE,
                        frames_per_buffer = self.CHUNK,
                        output = True,
                        stream_callback=stream_cb)


    self.stream.stop_stream()
    self.start()

  def run(self):
    print(self.log_prefix + 'audio io internal thread start!')
    if (self.blocking == True):
      if (self.input == True):
        while (self.term == False):
          if (self.started == True):
            if (self.stream_on == False):
              self.stream.start_stream()

            in_data = self.stream.read(self.CHUNK)
            ret = self.write_buffer(in_data)
          else:
            if (self.stream_on == True):
              self.stream.stop_stream()
              self.stream_on = False
            time.sleep(0.5)
      else:
        while (self.term == False):
          if (self.started == True):
            if (self.stream_on == False):
              self.stream.start_stream()

            ret, out_data = self.read_buffer()
            if (ret == True):
              self.stream.write(out_data)
          else:
            if (self.stream_on == True):
              self.stream.stop_stream()
              self.stream_on = False
            time.sleep(0.5)
    print(self.log_prefix + 'audio io internal thread end!')

  def start_io(self):
    self.at_first = False
    if (self.input == True):
      self.wr_idx = 0
      self.rd_idx = 0
      self.buffering = 0

    if (self.blocking == True):
      self.started = True
    else:
      self.stream.start_stream()

  def stop_io(self):
    if (self.blocking == True):
      self.started = False
    else:
      self.stream.stop_stream()
      self.at_first = True

  def close(self):
    if (self.blocking == True):
      self.term = True
      print(self.log_prefix + 'close join S')
      self.join()
      print(self.log_prefix + 'close join E')

    self.stream.stop_stream()
    self.stream.close()
    self.p.terminate()

  def inc_index(self, index):
    index += 1
    if (index == self.buffer_num):
      index = 0

    return index

  def read_buffer(self):
    self.lock.acquire()
    if (self.buffering == 0):
      ret = False
    else:
      self.read_buf = copy.deepcopy(self.buf[self.rd_idx])
      self.rd_idx = self.inc_index(self.rd_idx)
      self.buffering -= 1
      ret = True

    self.lock.release()
    return ret, self.read_buf

  def write_buffer(self, data):
    self.lock.acquire()
    if (self.buffering == self.buffer_num):
      if (self.debug == True):
        print (self.log_prefix + 'buffer full!  idx : ', self.rd_idx)

      ret = False
    else:
      self.buf[self.wr_idx] = copy.deepcopy(data)
      self.wr_idx = self.inc_index(self.wr_idx)
      self.buffering += 1
      ret = True

    self.lock.release()
    return ret

  def set_debug(self, debug):
    self.debug = debug

