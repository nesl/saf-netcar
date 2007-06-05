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

ACCELEROMETER_MODULE = 0x80
SAF_MODULE = 0x81

ACCELEROMETER_DATA = 33
MSG_ERROR_DATA = 34
LINE_DATA = 35

SAMPLES_PER_MSG = 30 
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

        #Sending events on "Connect" "Plot" and "Exit"
        wx.EVT_MENU(self, ID_CONNECT, self.OnConnect)
        wx.EVT_MENU(self, ID_EXIT, self.OnExit)
        wx.EVT_MENU(self, ID_PLOT, self.OnPlot)
        wx.EVT_MENU(self, ID_CHANGE, self.OnChange)

        self.client = plot.PlotCanvas(self)
        self.client.SetEnableLegend(True)
        self.Show(True)

        # log files recording difference in time stamps and when a different message type is sent
        self.time_log = open('time_report_' + str(logNum) + '.log', 'w')
  			self.standard_change_log = open('standard_change_' + str(logNum) + '.log', 'w')
        self.change_log = open('byte_report_' + str(logNum) + '.log', 'w')
				self.error_log = open('error_report_' + str(logNum) + '.log', 'w')
				self.avg_error_log = open('avg_error_report_' + str(logNum) + '.log', 'w')
				self.prediction_log = open('prediction_report_' + str(logNum) + '.log','w')

				self.line_recieved = 0;
        self.index = 0
        self.d0 = {}
        self.d1 = {}
        self.x_pred = {}
        self.y_pred = {}
        self.Ax = 0
        self.Bx = 0
        self.Ay = 0
        self.By = 0
				self.x_noise = 0
				self.y_noise = 0
        self.x_static_coef = [0,0,0,0,0,0]
        self.y_static_coef = [0,0,0,0,0,0]
				self.x_last_readings = [0,0,0,0,0,0]
				self.y_last_readings = [0,0,0,0,0,0]
				self.x_errors = [0]
				self.y_errors = [0]
				self.start_time = 0
				self.end_time = 0
				self.time_valid = 0
				self.start_valid_time = 0
				self.change_count = -1

        #count of line and error messages
        self.num_total_error_msg = 0
				self.num_real_errors = 0
				self.num_small_errors = 0
        self.num_error_msg = 0

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
				self.time_valid += self.end_time - self.start_valid_time

				print self.time_valid
				print self.end_time - self.start_time

				self.time_log.write("time_valid: " + str(self.time_valid))
				self.time_log.write("\ttime_running: " + str(self.end_time - self.start_time))
				self.time_log.write("\tavg_time_valid: " + str(self.time_valid / float(self.change_count))+ "\n")
        self.time_log.close()
        self.change_log.close()
				self.standard_change_log.close()
				self.error_log.close()
			  self.avg_error_log.close()
				self.prediction_log.close()
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
            if data == SAF_MODULE or data == ACCELEROMETER_MODULE:
                try:
                    s = self.sc.s.recv(7)
                    (src_mod, dst_addr, src_addr, msg_type, msg_length) = struct.unpack("<BHHBB", s)
                except struct.error:
                    print struct.error
                    print "bad msg header:", map(ord, s)
                #print src_mod, dst_addr, src_addr, msg_type, msg_length
                if msg_type == LINE_DATA or msg_type == ACCELEROMETER_DATA:
                    try:
                        s = self.sc.s.recv(4)
                        # remove the 4 time bytes from the message length
                        msg_length -= 4
                        (time_rx, ) = struct.unpack("<L", s)
												# fix me, don't do this if it is a simulation
                        time_rx /= TIME_CONV
                        computation_time = old_time_rx - (time_rx ) 

												print "line message"
												print time_rx
                        #self.time_log.write('difference between old timestamp and first new reading ' +  str(computation_time))
                        #self.time_log.write('\t number of readings ignored: ' +str(computation_time * SAMPLE_RATE) + '\n') 

                        old_time_rx = time_rx
                    except struct.error:
                        print struct.error
                        print "bad string for time:", map(ord, s)
                    
                    try:
                        s = self.sc.s.recv(SAMPLES_PER_MSG*2)
                        accel0 = struct.unpack("<"+SAMPLES_PER_MSG*'H', s)
                    except struct.error:
			                  print msg_length
                        print struct.error
                        print "bad string for accel0:", map(ord, s)
                    try:
                        s = self.sc.s.recv(SAMPLES_PER_MSG*2)
                        accel1 = struct.unpack("<"+SAMPLES_PER_MSG*'H', s)
                    except struct.error:
                        print struct.error
                        print "bad string for accel1:", map(ord, s)
										if msg_type == ACCELEROMETER_DATA:
										  if src_addr not in nodes.keys():
												nodes[src_addr] = {'last_seen': time_rx, 'file': open(str(src_addr)+".log", 'w')}
											else:

												d0 = []
												d1 = []
												x_prediction = []
												y_prediction = []

												for i in range(SAMPLES_PER_MSG):
													t = time_rx - (SAMPLES_PER_MSG-1-i)*TIME_INTERVAL
													d0.append((t, accel0[i]))
													d1.append((t, accel1[i]+100))
									        x_prediction.append((t, 0))
													y_prediction.append((t, 0))
													nodes[src_addr]['file'].write('%f\t%d\t%d\n'%(time_rx - (SAMPLES_PER_MSG-i)*TIME_INTERVAL, accel0[i], accel1[i]))
													
												nodes[src_addr]['last_seen'] = time_rx
											  wx.PostEvent(self, ResultEvent({'src_addr': src_addr, 'accel0': d0, 'accel1': d1, 'x_pred': x_prediction, 'y_pred': y_prediction}))

										  packet_size = 8 + 4 + SAMPLES_PER_MSG*2*2
											self.standard_change_log.write("ACCELEROMETER_data_size:\t"+str(packet_size)+"\treadings_lost:\t"+str(computation_time / TIME_INTERVAL ) + '\n')
										else:
											try:
													s = self.sc.s.recv(2 * 2 * 4)
													(Ax, Bx, Ay, By) = struct.unpack("<ffff",s)
											except struct.error:
													print struct.error
													print "bad string for linear coef", map(ord, s)
											try:
													s = self.sc.s.recv(NUM_STATIC_COEF * 4)
													x_static_coef = struct.unpack("<"+NUM_STATIC_COEF*"f", s)
											except:
													print struct.error
													print "bad string for x dim static coef", map(ord, s)
											try:
													s = self.sc.s.recv(NUM_STATIC_COEF*4)
													y_static_coef = struct.unpack("<"+NUM_STATIC_COEF*"f", s)
											except:
													print struct.error
													print "bad string for y dim static coef", map(ord,s)
											try:
											    s = self.sc.s.recv(8)
	                        (x_noise, y_noise) = struct.unpack("<ff", s)
											except:
   										    print struct.error
													print "bad string for noise factors", map(ord,s)

										 
											# try to find out the sample times
											if src_addr not in nodes.keys():
													#never seen the node before.
													nodes[src_addr] = {'last_seen': time_rx, 'file': open(str(src_addr)+".log", 'w')}
													self.start_time = time_rx - (SAMPLES_PER_MSG-1) * TIME_INTERVAL
													self.start_valid_time = self.start_time
											# reset the error counts and record the mean and variance of errors since the last line message
											mean = 0
											variance = 0
											for i in range(len(self.x_errors)):
												mean += self.x_errors[i]

											mean = mean / len(self.x_errors)

											for i in range(len(self.x_errors)):
												variance = (self.x_errors[i] - mean) * (self.x_errors[i] - mean)

											variance /= len(self.x_errors)

											self.avg_error_log.write('time: ' + str(time_rx))
											self.avg_error_log.write('\tx_noise: ' + str(self.x_noise) + '\tavg_x_error: ' + str(mean) + '\tvar_x_error: ' + str(variance))

											mean = 0
                      variance = 0
                      for i in range(len(self.y_errors)):
	                        mean += self.y_errors[i]
                      mean = mean / len(self.y_errors)
	
											for i in range(len(self.y_errors)):
												variance = (self.y_errors[i] - mean) * (self.y_errors[i] - mean)
                      variance /= len(self.y_errors)

											self.avg_error_log.write('\ty_noise: ' + str(self.y_noise) + '\tavg_y_error: ' + str(mean) + '\tvar_y_error: ' + str(variance) + '\n')

													#self.error_log.write('number_of_errors_since_line: ' + str(self.num_total_error_msg) + '\tnum_real_errors: ' + str(self.num_small_errors))
													#self.error_log.write('\tnum_outliers: ' + str(self.num_real_errors))
													#self.error_log.write('\tpercentage_OUTLIER_errors: ' + str(self.num_real_errors/float(self.num_total_error_msg)*100))
													#self.error_log.write('\tpercentage_real_errors: ' + str(self.num_small_errors/float(self.num_total_error_msg)*100) + '\n')
													
											self.end_time = time_rx;
											d0 = []
											d1 = []
											x_prediction = []
											y_prediction = []
											self.Ax = Ax
											self.Bx = Bx
											self.Ay = Ay
											self.By = By
											self.x_static_coef = x_static_coef
											self.y_static_coef = y_static_coef
											self.x_noise = x_noise
											self.y_noise = y_noise

											self.x_errors = []
											self.y_errors = []
											self.num_total_error_msg = 0
											self.num_real_errors = 0
											self.num_small_errors = 0
											self.num_error_msg = 0

											print (time_rx - (SAMPLES_PER_MSG-1)*TIME_INTERVAL ) - self.start_valid_time
											self.time_valid += (time_rx - (SAMPLES_PER_MSG-1)*TIME_INTERVAL ) - self.start_valid_time;
											self.change_count += 1
											self.start_valid_time  = time_rx;

											# correlate the samples with time
											# FIXME: this is only an estimate based on the reception time of the sampleu
											for i in range(SAMPLES_PER_MSG):
													t = time_rx - (SAMPLES_PER_MSG-1-i)*TIME_INTERVAL
													d0.append((t, accel0[i]))
													d1.append((t, accel1[i]+100))
													x_prediction.append((t, Ax*t + Bx )) # + x_noise*normal_random()  ))
													y_prediction.append((t, Ay*t + By  + 100 ))# + sqrt( y_noise )*normal_random() ))

											nodes[src_addr]['file'].write('%f\t%d\t%d\n'%(time_rx - (SAMPLES_PER_MSG-i)*TIME_INTERVAL, accel0[i], accel1[i]))

											t = time_rx - (SAMPLES_PER_MSG-1) * TIME_INTERVAL  
											for i in range(NUM_STATIC_COEF,SAMPLES_PER_MSG):
                          x_error = 0
                          y_error = 0
                          for j in range(NUM_STATIC_COEF):
                              x_error += x_static_coef[j] *  (accel0[i-NUM_STATIC_COEF+j] - (Ax *(t + j*TIME_INTERVAL) + Bx))
                              y_error += y_static_coef[j] *  (accel1[i-NUM_STATIC_COEF+j] - (Ay *(t + j*TIME_INTERVAL) + By))
                          x_prediction[i] = (x_prediction[i][0], x_prediction[i][1] + x_error)
                          y_prediction[i] = (y_prediction[i][0], y_prediction[i][1] + y_error)
											    self.x_errors.append(abs(d0[i][1] - x_prediction[i][1]) )
											   	self.y_errors.append(abs(d1[i][1] - y_prediction[i][1]) )
                          t += TIME_INTERVAL

											self.x_last_readings = []
											self.y_last_readings = []


											for i in range(SAMPLES_PER_MSG):
													self.prediction_log.write(str(d0[i][0]) + "\t" + str(d0[i][1]) + "\t" +  str(x_prediction[i][1]))
													self.prediction_log.write("\t" + str(d1[i][1]) + "\t" + str(y_prediction[i][1]) +'\n')

											self.line_recieved = 1
											for i in range(NUM_STATIC_COEF):
													self.x_last_readings.append( accel0[SAMPLES_PER_MSG - NUM_STATIC_COEF+i])
													self.y_last_readings.append( accel1[SAMPLES_PER_MSG - NUM_STATIC_COEF+i])

											nodes[src_addr]['last_seen'] = time_rx
											wx.PostEvent(self, ResultEvent({'src_addr': src_addr, 'accel0': d0, 'accel1': d1, 'x_pred': x_prediction, 'y_pred': y_prediction}))

											packet_size = 8 + 4 + 4*4 + NUM_STATIC_COEF*4*2 +NUM_DIMS*4
											self.change_log.write('LINE_data_size:\t' + str(packet_size) + "\ttime: " + str(time_rx))
											self.change_log.write('\treadings_lost:\t' +str(computation_time / TIME_INTERVAL) + '\n')
                    #print accel0
                    #print accel0
                elif msg_type == MSG_ERROR_DATA:
                    # x_pred_error = []
                    # y_pred_error = []
                    try:
                        s = self.sc.s.recv(4)
                        # remove the 4 time bytes from the message length
                        msg_length -= 4
                        (time_rx, ) = struct.unpack("<L", s)
												print "error message"
												print time_rx
                        time_rx /= TIME_CONV
#                        computation_time = old_time_rx - (time_rx - (SAMPLES_PER_MSG-1)/float(SAMPLE_RATE)) + 1/float(SAMPLE_RATE)
                        computation_time = old_time_rx - time_rx
                        #self.time_log.write('difference between old timestamp and first new reading ' + str(computation_time))
                        #self.time_log.write('\t number of readings ignored: ' + str(computation_time* SAMPLE_RATE) + '\n')
                        
                        old_time_rx = time_rx
                    except struct.error:
                        print struct.error
                        print "bad string for time:", map(ord, s)
										try:
										    s = self.sc.s.recv(NUM_DIMS*2)
	                      (accl0, accl1) = struct.unpack("<"+NUM_DIMS*"H", s)
										except struct.error:
										   print msg_length
											 print struct.error
											 print "bad string for accl0 and accel1", map(ord,s)
                    try:
                        s = self.sc.s.recv(4)
                        (x_pred_error, ) = struct.unpack("<f", s)
                    except struct.error:
                        print msg_length
                        print struct.error
                        print "bad string for x_pred_error:", map(ord, s)
                    try:
                        s = self.sc.s.recv(4)
                        (y_pred_error, ) = struct.unpack("<f", s)
                    except struct.error:
                        print msg_length
                        print struct.error
                        print "bad string for y_pred_error:", map(ord, s)
										try:
									      s = self.sc.s.recv(2)
												(is_real_msg, ) = struct.unpack("<H", s)
										except struct.error:
										    print msg_length
												print struct.error
												print "bad string for is_real_msg:", map(ord, s)
                    if src_addr not in nodes.keys():
											#never seen the node before.
											nodes[src_addr] = {'last_seen': time_rx, 'file': open(str(src_addr)+".log", 'w')}
                    else:
										  if self.num_error_msg == 0:
                        d0 = []
											  d1 = []
                        x_prediction = []
												y_prediction = []

											self.num_total_error_msg += 1

										  x_error = 0
											y_error = 0
											t = time_rx - (NUM_STATIC_COEF - 1) * TIME_INTERVAL
											for i in range(NUM_STATIC_COEF):
												x_error += self.x_static_coef[i]*(self.x_last_readings[i] - (self.Ax *(t + i*TIME_INTERVAL) + self.Bx))
                        y_error += self.y_static_coef[i]*(self.y_last_readings[i] - (self.Ay *(t + i*TIME_INTERVAL) + self.By))

											self.end_time = time_rx;

											self.x_last_readings.pop(0)
	                    self.y_last_readings.pop(0)

											d0.append((time_rx, accl0))
	                    d1.append((time_rx, accl1 + 100))

											if (is_real_msg == 1):
											  self.num_real_errors += 1
											  packet_size = 8 + 4 + NUM_DIMS*2 + 4*2
											  self.change_log.write('OUTLIER:\t' + str(packet_size))
												self.change_log.write('\ttime_of_error:\t' + str(time_rx))
												self.change_log.write('\tX_ERROR:\t' + str(x_pred_error))
												self.change_log.write('\tY_ERROR:\t' + str(y_pred_error) )
											  self.change_log.write('\treadings_lost:\t' +str(computation_time / TIME_INTERVAL) + '\n')
											elif (is_real_msg == 2):
											  self.num_small_errors +=1
												packet_size = 8 + 4 + NUM_DIMS*2 + 4*2
												self.change_log.write('REAL:\t' + str(packet_size))
												self.change_log.write('\ttime_of_error:\t' + str(time_rx))
												self.change_log.write('\tX_ERROR:\t' + str(x_pred_error))
												self.change_log.write('\tY_ERROR:\t' + str(y_pred_error) )
  											self.change_log.write('\treadings_lost:\t' +str(computation_time / TIME_INTERVAL) + '\n')
											else:
												packet_size = 8 + 4 + NUM_DIMS*2 + 4*2
												#self.change_log.write('NOT_REAL:\t' + str(packet_size))
                        #self.change_log.write('\ttime_of_error:\t' + str(time_rx))
                        #self.change_log.write('\tX_ERROR:\t' + str(x_pred_error))
                        #self.change_log.write('\tY_ERROR:\t' + str(y_pred_error) + '\n')
												x_pred_error = 0
												y_pred_error = 0


											x_pred = self.Ax*time_rx + self.Bx + x_error + x_pred_error #+ self.x_noise*normal_random()
											y_pred = self.Ay*time_rx + self.By + y_error + y_pred_error + 100 #+ sqrt(self.y_noise )*normal_random()

	                    x_prediction.append((time_rx, x_pred ))
	                    y_prediction.append((time_rx, y_pred ))
                      
											self.prediction_log.write(str(time_rx) + "\t" + str(accl0) + "\t" +  str(x_pred))
	                    self.prediction_log.write("\t" + str(accl1+100) + "\t" + str(y_pred) +'\n')

	                    self.x_errors.append(abs(accl0 - x_pred)) 
										  self.y_errors.append(abs(accl1 - (y_pred - 100)))

											if (self.line_recieved == 1):
	                      self.error_log.write('time: ' + str(time_rx) + '\tx_error: ' + str(abs(accl0-x_pred)) + '\ty_error: ' + str(abs(accl1-(y_pred-100))) + '\n')	
											if (is_real_msg == 0):
	                      self.x_last_readings.append(x_pred)
	                      self.y_last_readings.append(y_pred-100)
										  else:
												self.x_last_readings.append(accl0)
												self.y_last_readings.append(accl1)

	                    self.num_error_msg += 1

											print "number of error messages"
											print self.num_error_msg
											
											if self.num_error_msg == SAMPLES_PER_MSG-1:
											  self.num_error_msg = 0
												nodes[src_addr]['last_seen'] = time_rx
											 	wx.PostEvent(self, ResultEvent({'src_addr': src_addr, 'accel0': d0, 'accel1': d1, 'x_pred':x_prediction, 'y_pred': y_prediction}))	


                lastdata = -1
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

