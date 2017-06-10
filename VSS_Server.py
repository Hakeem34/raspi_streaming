# -*- coding:utf-8 -*-
#!/usr/bin/python

import SocketServer
import cv2
import numpy
import socket
import sys
import threading
import time
from audio_io import AudioIo
from contextlib import closing


#環境に応じて変更
local_address   = '192.168.64.31' # 送信側のPCのIPアドレス
multicast_group = '239.255.0.1'   # マルチキャストアドレス
PORT_V = 4000
PORT_S = 4001
SEND_SIZE = 1040
my_addr='0.0.0.0' #これは変えない
multi_address=(my_addr, PORT_S)
bufsize = 4096



capture = cv2.VideoCapture(0)
capture.set(3,640)
capture.set(4,480)
small = True
send_count = 0
rcv_count = 0
prev_send = 0
prev_rcv = 0

class PerfThread(threading.Thread):
    def __init__(self):
      super(PerfThread, self).__init__()
      self.perf = False
      self.term = False

    def run(self):
      global send_count
      global rcv_count
      global prev_send
      global prev_rcv

      while (True):
        if (self.perf == True):
          print('send count:', send_count, send_count-prev_send)
          print('rcv count:', rcv_count, rcv_count-prev_rcv)
          prev_send = send_count
          prev_rcv = rcv_count

        time.sleep(1)
        if (self.term == True):
          break



class SoundThread(threading.Thread):
    def __init__(self):
      super(SoundThread, self).__init__()
      self.setDaemon(True)
      self.term = False
      self.audio_in = AudioIo(True, 16000, 2, True)
      self.audio_out = AudioIo(False, 16000, 0, True)
#     self.audio_out.set_debug(True)
      self.upper_audio = False
      self.out_mode = False

    def run(self):
      global send_count
      global rcv_count

      print " === start sub thread (sub class) === "
      print("MultiSock 1")
      with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
        print("MultiSock 2")
        sock.bind(multi_address)
        print("MultiSock 3")
        mreq=socket.inet_aton(multicast_group)+socket.inet_aton(local_address)
        print("MultiSock 4")
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        print("MultiSock 5")
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(local_address))
        print("MultiSock 6")
        sock.settimeout(1.0)
        self.audio_in.start_io()
        while (self.term == False):
          if (self.upper_audio == True):
            if (self.out_mode == False):
              self.audio_out.start_io()
              self.out_mode = True

            try:
              data = sock.recv(bufsize)
              rcv_count += 1
#             print len(data)
              self.audio_out.write_buffer(data)
            except socket.timeout:
#             print('upper audio socket timeout!')
              pass
          else:
            if (self.out_mode == True):
              self.audio_out.stop_io()
              self.out_mode = False

            ret, input = self.audio_in.read_buffer()
            if (ret == True):
              send_count += 1
#             print len(input)
              sock.sendto(input, (multicast_group, PORT_S))

      self.audio_in.stop_io()
      self.audio_in.close()
      print " === end sub thread (sub class) === "
      return


ST = SoundThread()
PT = PerfThread()

class TCPHandler(SocketServer.BaseRequestHandler):
    #リクエストを受け取るたびに呼ばれる関数
    def handle(self):
        global capture
        global small
        global ST
        global PT
        global prev_send
        global prev_rcv

        #VIDEOを受け取ったらJPEG圧縮したカメラ画像を文字列にして送信
#       self.data = self.request.recv(1040).strip()
        self.data = self.request.recv(1040)
        self.cmd = self.data[:5]
        
        if (self.cmd == 'VIDEO'):
          ret, frame=capture.read()
          if (ret == False):
            print ret
            self.request.send('no image')
          else:
            if (small == True):
              frame = cv2.resize(frame, (320,240))

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY),90]  
            result,jpeg_data = cv2.imencode('.jpg',frame,encode_param)
#           print(len(jpeg_data))
            self.request.send(jpeg_data)

        if (self.cmd == 'LARGE'):
          print('LARGE')
          small = False

        if (self.cmd == 'SMALL'):
          print('SMALL')
          small = True

        if (self.cmd == 'TALKS'):
          print('Talk Start')
          ST.upper_audio = True

        if (self.cmd == 'TALKE'):
          print('Talk End')
          ST.upper_audio = False

        if (self.cmd == 'AUDIO'):
          print('Audio')
          self.audio_data = self.data[16:]
          ST.audio_out.write_buffer(self.audio_data)

        if (self.cmd == 'TERM '):
          print('TERM')
          ST.audio_out.stop_io()
          ST.audio_out.close()
          self.request.close()
          self.server.server_close()

        if (self.cmd == 'GETIP'):
          print('request from:', self.client_address)
          self.request.send(str(self.client_address))

        if (self.cmd == 'PERFS'):
          print('send count:', send_count)
          print('rcv count:', rcv_count)
          prev_send = send_count
          prev_rcv = rcv_count
          PT.perf = True

        if (self.cmd == 'PERFE'):
          PT.perf = False

def main():
  #カメラの設定
  if not capture:
      print "Could not open camera"
      sys.exit()

  ST.start()
  PT.start()

  print("SockServer 1")
  SocketServer.TCPServer.allow_reuse_address = True
  print("SockServer 2")
  server = SocketServer.TCPServer((local_address, PORT_V), TCPHandler)
  print("SockServer 3")

  #^Cを押したときにソケットを閉じる
  try:
      server.serve_forever()
  except KeyboardInterrupt:
      pass
  except socket.error:
      print('socket.error!')
      pass

  ST.term = True
  PT.term = True
  print('before join')
  ST.join()
  PT.join()
  print('after join')

  server.shutdown()
  capture.release()
  cv2.destroyAllWindows()

  sys.exit()

if __name__ == '__main__':
  main()


