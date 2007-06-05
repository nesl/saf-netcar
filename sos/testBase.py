#!/usr/bin/python
# -*- Mode: C; tab-width:2 -*- 
# ex: set ts=2 shiftwidth=2 softtabstop=2 cindent: 

import getopt, sys
import thread
import random 
from math import sqrt
import socket
import sys
import struct
import time
import wx
import wx.lib.plot as plot
import ProcessSOSMessage

ACCELEROMETER_MODULE = 0x80
SAF_MODULE = 0x81

ACCELEROMETER_DATA = 33
MSG_ERROR_DATA = 34
LINE_DATA = 35

SAMPLES_PER_MSG = 30 
NUM_LINEAR_COEF =2
NUM_STATIC_COEF = 6 
NUM_DIMS = 2

TIME_INTERVAL = .0195
SAMPLE_RATE = .0512
TIME_CONV = 115200.0

#TIME_INTERVAL = 2346
#TIME_CONV = 1

EVT_RESULT_ID = wx.NewId()

ID_CONNECT = 101
ID_EXIT = 110
ID_PLOT = 102
ID_CHANGE = 103
# global varialbes 
WINDOWSIZE = 1200

collist = ['green',
           'red',
           'blue',
           'cyan']
pred_collist = [ 'purple',
                 'brown'] 
              
def normal_random():
		X = 0
		for i in range(20):
				X += random.random()

		X -= 10
		X *= sqrt(12/float(20))

    return X

def EVT_RESULT(win, func):
    """Define Result Event."""
    win.Connect(-1, -1, EVT_RESULT_ID, func)

class ResultEvent(wx.PyEvent):
    """Simple event to carry arbitrary result data."""
    def __init__(self, data):
        """Init Result Event."""
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_RESULT_ID)
        self.data = data

class SocketClient:
    """ """
    def __init__(self, host,port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected=1

        try:
            self.s.connect((host, port))
        except socket.error:
            self.connected=0
        self.data=""


    def close(self):
        if(self.connected):
            self.s.shutdown(2)
            self.s.close()

    def send(self, command):
        if(self.connected):
            self.s.send(command)
        else:
            print "Error: No connection to command server..."


class BaseStation(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title, size=(180, 280))

				try: 
					print sys.argv
					opts, args = getopt.getopt(sys.argv[1:], 'n:'	)
				except getopt.GetoptError:
					print "bad?"
					sys.exit(2)

				for o, a in opts:
					if o == "-n":
						logNum = a;
        # Setting up the menu
        filemenu = wx.Menu()
        filemenu.Append(ID_CONNECT, "&Connect", " Connect to a live stream of data")
        filemenu.Append(ID_PLOT, "&Plot", " Plot an existing stream of data from a file")
        filemenu.Append(ID_CHANGE, "&Change", " Change epsilon and number of errors in mode")
        filemenu.AppendSeparator()
        filemenu.Append(ID_EXIT,"E&xit", " Terminate the program")
        # Creating the menubar
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu, "&Menu") # Adding the "filemenu" to menubar
        self.SetMenuBar(menuBar) # Adding menubar to the frame content

				self.d0 = {}
				self.d1 = {}
				self.x_pred = {}
				self.y_pred = {}
				self.num_error_msg = 0

        #Sending events on "Connect" "Plot" and "Exit"
        wx.EVT_MENU(self, ID_CONNECT, self.OnConnect)
        wx.EVT_MENU(self, ID_EXIT, self.OnExit)
        wx.EVT_MENU(self, ID_PLOT, self.OnPlot)
        wx.EVT_MENU(self, ID_CHANGE, self.OnChange)

        self.client = plot.PlotCanvas(self)
        self.client.SetEnableLegend(True)
        self.Show(True)

				self.p = ProcessSOSMessage.ProcessSOSMessage(TIME_CONV, TIME_INTERVAL, SAMPLES_PER_MSG, NUM_LINEAR_COEF,NUM_STATIC_COEF,2)

        EVT_RESULT(self,self.OnResult)

    # Handlers for events on "Connect" "Plot" and "Exit"
    def OnConnect(self, e):
        d = wx.MessageDialog(self, "Hit Connect"
                             " in python", "blah", wx.OK)
        d.ShowModal()
        d.Destroy()
        self.sc = SocketClient("127.0.0.1", 7915)
        try:
            thread.start_new_thread(self.input_thread, ())
        except thread.error:
            print error

        try:
            thread.start_new_thread(self.output_thread, ())
        except thread.error:
            print error
    def OnPlot(self, e):
        d = wx.MessageDialog(self, "Hit Plot"
                             " in python", "blah", wx.OK)
        d.ShowModal()
        d.Destroy()

    def OnChange(self, e):
        #d = wx.NumberEntryDialog(self, "Enter new epsilon" "for fun", "changes are fun", 1, 0, 100)
        d = wx.TextEntryDialog(self, "change epsilon", "fun!","replace me", wx.OK)
        d.ShowModal()
        new_value = float(d.GetValue())
        #print new_value
        d.Destroy()
    def OnExit(self, e):
        self.Close(True)

    def OnResult(self, event):

        src_addr = event.data['src_addr']
        accel0 = event.data['accel0']
        accel1 = event.data['accel1']
        x_pred = event.data['x_pred']
        y_pred = event.data['y_pred']

        if src_addr not in self.d0.keys():
            self.d0[src_addr] = []
            self.d1[src_addr] = []
            self.x_pred[src_addr] = []
            self.y_pred[src_addr] = []
        self.d0[src_addr] += accel0
        self.d1[src_addr] += accel1
        self.y_pred[src_addr] += y_pred
        self.x_pred[src_addr] += x_pred

        self.d0[src_addr][0:max(-WINDOWSIZE, -len(self.d0[src_addr]))] = []
        self.d1[src_addr][0:max(-WINDOWSIZE, -len(self.d1[src_addr]))] = []
        self.x_pred[src_addr][0:max(-WINDOWSIZE, -len(self.x_pred[src_addr]))] = []
        self.y_pred[src_addr][0:max(-WINDOWSIZE, -len(self.y_pred[src_addr]))] = []
    
        lines = []
        i=0
        for src_addr in self.d0.keys():
            lines.append(plot.PolyLine(self.d0[src_addr], legend=str(src_addr)+' accel0', colour=collist[i], width=1))
            lines.append(plot.PolyLine(self.d1[src_addr], legend=str(src_addr)+' accel1', colour=collist[i], width=1))
            lines.append(plot.PolyLine(self.x_pred[src_addr], legend=str(src_addr)+' x_pred', colour=pred_collist[i], width=1))
            lines.append(plot.PolyLine(self.y_pred[src_addr], legend=str(src_addr)+' y_pred', colour=pred_collist[i], width=1))
            i += 1
        gc = plot.PlotGraphics(lines, 'Accelerations', 'Time [s]', 'Acceleration 10bit')
        # the X axis shows the last 500 samples
        self.client.Draw(gc, xAxis= (self.d0[src_addr][max(-WINDOWSIZE+100, -len(self.d0[src_addr]))][0], self.d0[src_addr][-1][0]), yAxis= (0,1024))



    def input_thread(self):
        """ currently we don't use the input thread.
        """
        pass

    def output_thread(self):
        lastdata = -1
        nodes = {}
        old_time_rx = 0
        start_time = time.time()
        while 1:
            data = ord(self.sc.s.recv(1))
            #print data, ACCELEROMETER_MODULE
						if (data == SAF_MODULE or data == ACCELEROMETER_MODULE):
              try:
                  s = self.sc.s.recv(7)
                  (src_mod, dst_addr, src_addr, msg_type, msg_length) = struct.unpack("<BHHBB", s)
              except struct.error:
                  print struct.error
                  print "bad msg header:", map(ord, s)

  					  if (msg_type == ACCELEROMETER_DATA):
	  						plot_values = self.p.ProcessAccelData(self.sc.s, 100)
 
								print "printing new line"
	  						wx.PostEvent(self, ResultEvent({'src_addr': src_addr, 'accel0': plot_values[0], 'accel1': plot_values[1], 'x_pred': plot_values[0], 'y_pred': plot_values[1]}))

		  					lastdata = -1;
			  		  elif (msg_type == LINE_DATA):
								print "processing line data"
				  			(plot_values, pred_values) = self.p.ProcessLineData(self.sc.s, 100)
								
								self.num_error_msg = 0
										
								wx.PostEvent(self, ResultEvent({'src_addr': src_addr, 'accel0': plot_values[0], 'accel1': plot_values[1], 'x_pred': pred_values[0], 'y_pred': pred_values[1]}))

					  		lastdata= -1
							elif (msg_type == MSG_ERROR_DATA):
								(accel_value, pred_value) = self.p.ProcessErrorData(self.sc.s, 100)

							  if (self.num_error_msg == 0):
									d0 = []
									d1 = []
									y_pred = []
									x_pred = []

							  d0.append(accel_value[0][0])
								d1.append(accel_value[1][0])
								x_pred.append(pred_value[0][0])
								y_pred.append(pred_value[1][0])
			
								self.num_error_msg += 1

								if (self.num_error_msg == SAMPLES_PER_MSG -1):
									print "printing set of error messages"

									self.num_error_msg= 0
								  wx.PostEvent(self, ResultEvent({'src_addr': src_addr, 'accel0': d0, 'accel1': d1, 'x_pred': x_pred, 'y_pred': y_pred}))
  						else:
	  						lastdata = data
								

class MyApp(wx.App):
    def OnInit(self):
        frame = BaseStation(None, -1, 'Plotting')
        frame.Show(True)
        self.SetTopWindow(frame)

        return True

if(__name__ == "__main__"):

    app = MyApp(0)
    app.MainLoop()

