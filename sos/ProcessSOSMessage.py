import struct
import time
from math import sqrt


class ProcessSOSMessage:
	def __init__(self, time_c, time_i, samples_per_m, num_l, num_AR, num_d):
		self.time_conv = time_c
		self.time_interval = time_i
		self.samples_per_msg = samples_per_m
		self.num_linear_coef = num_l
		self.num_static_coef = num_AR
		self.num_dim = num_d

		self.linear = [] 
		self.static = []
		self.noise = []
		self.last_reading = []
		
		for i in range(self.num_dim):
			self.linear.append([])
			for j in range(self.num_linear_coef):
				self.linear[i].append(0)

		for i in range(self.num_dim):
                        self.static.append([])
                        for j in range(self.num_static_coef):
                                self.static[i].append(0)

		for i in range(self.num_dim):
                        self.noise.append(0)

		for i in range(self.num_dim):
			self.last_reading.append([])
			for j in range(self.num_static_coef):
				self.last_reading[i].append(0)

		
	# input is a strut with 4 bytes holding the time value
	# returns the time value converted according to the time_conv value
	def ProcessTime(self, sock):
		try:
			s = sock.recv(4)

			(time_rx,)  = struct.unpack("<L", s)
			time_rx /= self.time_conv
		except struct.error:
			print struct.error
			print "bad string for time: "
	
		return time_rx
	# input is a struct holding samples_per_msg * num_dim * 2 bytes that we will unpack
	# returns the data as a 2 dimmensional array where the first dim is the accelerometer
	# and the second dimension holds the values
	def ProcessAccelValue(self, sock):
		accel_data = []
		
		for i in range(self.num_dim):
			try:
				s = sock.recv(self.samples_per_msg * 2)
                	        accel_data.append( struct.unpack("<"+self.samples_per_msg*'H', s) )
	                except struct.error:
        	                print struct.error

		return accel_data

	# input is a struct holding the linear, static, and noise coeficients that need to be unpacked
	# the data must be coming from the SAF module
	# returns the linear, static and noise coeficients for each accelerometer
	# the first dimension of each will be the accelerometer number
	# for second dimension of linear coef, 0 is A and 1 is B
	# for static coef, 0 is coef 0 and 1 is coef 1 and so on 
	# for noice coef, there is only one
	def ProcessLineValue(self, sock):
		lineCoef = []
		staticCoef = []
		noiseCoef = []

		for i in range(self.num_dim):
			try:
				s = sock.recv(self.num_linear_coef * 4)
				lineCoef.append( struct.unpack("<" + self.num_linear_coef*'f', s) )
			except struct.error:
				print struct.error
				print "bad string for linear coef data: " + str(i)
			
		for i in range(self.num_dim):
                        try:
				s = sock.recv(self.num_static_coef * 4)
                                staticCoef.append( struct.unpack("<" + self.num_static_coef*'f', s))
                        except struct.error:
                                print struct.error
                                print "bad string for linear coef data: " + str(i)
		
		for i in range(self.num_dim):
                        try:
				s = sock.recv(4)
                                noiseCoef.append( struct.unpack("<f", s))
                        except struct.error:
                                print struct.error
                                print "bad string for linear coef data: " + str(i)
			
		return (lineCoef, staticCoef, noiseCoef)					

	def ProcessLineData(self, sock, dist):
		time_rx = self.ProcessTime(sock)

		accel_data = self.ProcessAccelValue(sock)

		(linear_coef, static_coef, noise_coef) = self.ProcessLineValue(sock)

		self.linear = linear_coef
		self.static = static_coef
		self.noise = noise_coef
		self.last_reading = []

		plot_values = []
		pred_values = []

		for i in range(self.num_dim):
			plot_values.append([])
			pred_values.append([])
			
			a = linear_coef[i][0]
			b = linear_coef[i][1]
		
			for j in range(self.samples_per_msg):	
				t = time_rx - (self.samples_per_msg - i -1)*self.time_interval
				plot_values[i].append((t, accel_data[i][j] + i*dist ))
				pred_values[i].append((t, a*t + b + i*dist ))

			t = time_rx - (self.samples_per_msg -1)*self.time_interval
			for j in range(self.num_static_coef, self.samples_per_msg):
				error = 0
				for k in range(self.num_static_coef):
					error += static_coef[i][k] * (accel_data[i][j-self.num_static_coef+k] - (a*(t+k*self.time_interval) + b))
				pred_values[i][j] = (pred_values[i][j][0], pred_values[i][j][1] + error)
				t += self.time_interval

			self.last_reading.append([])
			for j in range(self.num_static_coef):
				self.last_reading[i].append(accel_data[i][self.samples_per_msg - self.num_static_coef + j])				

		return (plot_values, pred_values)

	def ProcessErrorValue(self, sock):
		accel_values = []
		error_values = []

		for i in range(self.num_dim):
			try:
				s = sock.recv(2)
				accel_values.append( struct.unpack("<H", s ))
			except struct.error:
				print struct.error
				print "bad string for single accel value: " + str(i)
		
		for i in range(self.num_dim):
			try:
				s = sock.recv(4)
				error_values.append( struct.unpack("<f", s) )
			except struct.error:
				print struct.error
				print "bad string for prediction error: " + str(i)

		try:
			s = sock.recv(2)
			(error_type, ) = struct.unpack("<H", s)
		except struct.error:
			print struct.error
			print "bad string for error type"

		return (accel_values, error_values, error_type)

	def ProcessErrorData(self, sock, dist):
		time_rx = self.ProcessTime(sock)

		(accel_value, error_values, error_type) = self.ProcessErrorValue(sock)

		pred_values = []
		accel_values = []
		for i in range(self.num_dim):
			pred_values.append([])
			accel_values.append([])

			error = 0
			t = time_rx - (self.num_static_coef) * self.time_interval
			for j in range(self.num_static_coef):
                        	error += self.static[i][j] * (self.last_reading[i][j] - (self.linear[i][0]*(t+j*self.time_interval) + self.linear[i][1]))			
			pred = self.linear[i][0]*time_rx + self.linear[i][1] + error

			pred_values[i].append( (time_rx, pred + i*dist) )
			accel_values[i].append( (time_rx, accel_value[i][0] + i*dist ) )

			for j in range(self.num_static_coef-1):
				self.last_reading[i][j] = self.last_reading[i][j+1]

			if error_type != 0:
				self.last_reading[i][self.num_static_coef-1] = accel_value[i][0]
			else:
				self.last_reading[i][self.num_static_coef-1] =  pred 
		return (accel_values, pred_values)

			
	# this is use for processing accelerometer data
	# we assume the header bits have already been read
	# the return values will be the samples for each of the accelerometers
	# the third arguement is the distance we want between each set of accelerometer values
	def ProcessAccelData(self, sock, dist):
		time_rx = self.ProcessTime(sock)
		
		accel_data = self.ProcessAccelValue(sock) 

		plot_values = []

		for i in range(self.num_dim):
			plot_values.append([])
			for j in range(self.samples_per_msg):
				t = time_rx - (self.samples_per_msg - j -1) * self.time_interval
				plot_values[i].append((t, accel_data[i][j] + i * dist))
		return plot_values			
				
			
