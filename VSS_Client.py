# -*- coding:utf-8 -*-
#!/usr/bin/python
import socket
import numpy
import cv2
import pyaudio
import threading
import time
import copy
from contextlib import closing
from audio_io import AudioIo

server_address  = '192.168.64.31' # 送信側のPCのIPアドレス
local_address   = '192.168.64.52' # 受信側のPCのIPアドレス
multicast_group = '239.255.0.1' # マルチキャストアドレス
bufsize = 4096

PORT_V = 4000
PORT_S = 4001
TALK_LOOP = False

my_addr='0.0.0.0' #これは変えない
multi_address=(my_addr, PORT_S)


debug = False
perf = False
send_count = 0
rcv_count = 0
prev_send = 0
prev_rcv = 0
term = False

class SoundClientThread(threading.Thread):
    def __init__(self):
      super(SoundClientThread, self).__init__()
      self.setDaemon(True)
      self.mic_on = True
      try:
        self.audio_in = AudioIo(True, 16000, 0, False, 8)
      except IOError:
        print('No Mic device')
        self.mic_on = False

      self.audio_out = AudioIo(False, 16000, 0, False, 32)
#     self.audio_out.set_debug(True)
      self.talk = False
      self.talk_mode = False

    def run(self):
      global send_count
      global rcv_count
      global term

      with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
        sock.bind(multi_address)
        mreq=socket.inet_aton(multicast_group)+socket.inet_aton(local_address)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        count = 0
        ret = True
        while (ret == True):
          ret = self.audio_out.write_buffer(sock.recv(bufsize))

        self.audio_out.start_io()
        start_time = time.time()
        while (term == False):
          if (self.talk == True):
            if (self.talk_mode == False):
              if (TALK_LOOP == False):
                self.audio_out.stop_io()
              self.audio_in.start_io()
              self.talk_mode = True
              set_cmd('TALKS\n')

            ret, data = self.audio_in.read_buffer()
            while (ret == False):
              time.sleep(0.1)
              ret, data = self.audio_in.read_buffer()

#           send_audio(data)
            send_count += 1
#           print len(data)
            sock.sendto(data, (multicast_group, PORT_S))

          else:
            if (self.talk_mode == True):
              self.audio_in.stop_io()
              if (TALK_LOOP == False):
                self.audio_out.start_io()
              self.talk_mode = False
              set_cmd('TALKE\n')

            data = sock.recv(bufsize)
#           print len(data)
            rcv_count += 1

          if ((self.talk_mode == False) or (TALK_LOOP == True)):
            self.audio_out.write_buffer(data)

          count += 1
          if (count == 10):
            now_time = time.time()
            if (debug == True):
              print (now_time - start_time, self.audio_out.buffering)

            start_time = now_time
            count = 0

      self.audio_out.stop_io()
      self.audio_out.close()


def getimage():
  #IPアドレスとポート番号は環境に応じて変更
  sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
  sock.connect((server_address,PORT_V))
  sock.send('VIDEO\n')
  buf=''
  recvlen=100
  while recvlen>0:
    receivedstr = sock.recv(1024*8)
    recvlen = len(receivedstr)
    buf += receivedstr
  sock.close()
  narray = numpy.fromstring(buf,dtype='uint8')
  return cv2.imdecode(narray,1)

def send_audio(data):
  #IPアドレスとポート番号は環境に応じて変更
  sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
  sock.connect((server_address,PORT_V))
  sock.send('AUDIO           ' + data)

def set_cmd(cmd):
  #IPアドレスとポート番号は環境に応じて変更
  sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
  sock.connect((server_address,PORT_V))
  sock.send(cmd)

def get_ip():
  #IPアドレスとポート番号は環境に応じて変更
  sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
  sock.connect((server_address,PORT_V))
  sock.send('GETIP\n')

  buf=''
  recvlen=100
  while recvlen>0:
    receivedstr = sock.recv(1024*8)
    recvlen = len(receivedstr)
    buf += receivedstr
  sock.close()
  print (buf)
  front = buf.find("'", 0)
  rear = buf.find("'", front+1)
  return buf[front+1:rear]


def perf_disp():
  global send_count
  global rcv_count
  global prev_send
  global prev_rcv
  global perf
  global term

  while (True):
    if (perf == True):
      print('send count:', send_count, send_count-prev_send)
      print('rcv count:', rcv_count, rcv_count-prev_rcv)
      prev_send = send_count
      prev_rcv = rcv_count

    time.sleep(1)
    if (term == True):
      break


def main():
  global debug
  global perf
  global term
  global prev_send
  global prev_rcv
  global local_address

  local_address = get_ip()

  video_on = True
  SCT = SoundClientThread()
  SCT.start()

  PerfTh = threading.Timer(1, perf_disp)
  PerfTh.start()

  print('q : quit')
  print('e : inate server')
  print('v : video on')
  print('n : video off')
  print('s : small video(QVGA)')
  print('l : large video(VGA)')
  print('d : debug')
  print('t : start/stop talk')
  while True:
    if ((video_on == True) and (SCT.talk == False)):
      img = getimage()
#      if len(img.shape) == 3:
#        height, width, channels = img.shape[:3]
#      else:
#        height, width = img.shape[:2]
#      if (width == 0) or (heigth == 0):
      if img == None:
        img = cv2.imread("noimage.png", cv2.IMREAD_UNCHANGED)

      cv2.imshow('Capture',img)

    in_key = cv2.waitKey(1) & 0xFF
    if in_key == ord('q'):
      term = True
      SCT.join()
      break

    if in_key == ord('g'):
      ip = get_ip()
      print ip

    if in_key == ord('e'):
      set_cmd('TERM \n')
      term = True
      SCT.join()
      break

    if in_key == ord('p'):
      if (perf == True):
        set_cmd('PERFE\n')
        perf = False
      else:
        set_cmd('PERFS\n')
        perf = True
        print('send count:', send_count)
        print('rcv count:', rcv_count)
        prev_send = send_count
        prev_rcv = rcv_count

    if in_key == ord('s'):
      set_cmd('SMALL\n')

    if in_key == ord('l'):
      set_cmd('LARGE\n')

    if in_key == ord('n'):
      video_on = False
      print ('video off')

    if in_key == ord('v'):
      video_on = True
      print ('video on')

    if in_key == ord('d'):
      debug = not(debug)
      print ('debug', debug)
      SCT.audio_out.set_debug(debug)
      if (SCT.mic_on == True):
        SCT.audio_in.set_debug(debug)

    if in_key == ord('t'):
      if (SCT.mic_on == True):
        if (SCT.talk == False):
          print ('Start Talk!')
          SCT.talk = True
        else:
          print ('Stop Talk!')
          SCT.talk = False

  term = True
  PerfTh.join()
  cv2.destroyAllWindows()

if __name__ == '__main__':
  main()

