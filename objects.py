# =============================================================================
# Proceso de Adquisición de Datos
# =============================================================================
import serial
import struct
import csv
from datetime import datetime
import numpy as np
from serial.tools import list_ports
import time
import matplotlib.pyplot as plt
import multiprocessing
from multiprocessing import Process, Queue, Event
import winsound  # Permite generar sonidos en sistemas Windows
from functions import LowPassFilter

# =============================================================================
# Funciones auxiliares
# =============================================================================
def buffer_management( buffer, enable, queue, threshold,
	printV=False, n_it=0,
	start_time_loop=0):	
	
	min_len = min(len(lst) for lst in buffer.values())

	n_it =  n_it + 1 if printV else n_it
	if min_len >= threshold:
		if printV:
			elapsed = time.time() - start_time_loop
			print("elapsed time : %.4f, n_it %s =================" % (
				elapsed, n_it ))
		buffer_publish = {}
		for j, data in buffer.items():
			buffer_publish[j] = data[:threshold]
			buffer[j] = data[threshold:]
			if printV:
				print(f"Para el cuerpo {j} el tamaño es {len(data)}")
				n_it = 0		
		if enable.is_set():
			queue.put(buffer_publish)
	return queue, buffer, n_it

# =============================================================================
# Proceso de Adquisición de Datos
# =============================================================================
class DataAdquisition(Process):
	def __init__(self, queue_save, queue_plot,  queue_process, stop_event, 
							enable_plot=Event(), enable_process=Event(), enable_save=Event(),
							acquisition_active=None):
		""" Inicializa el proceso de adquisición de datos.
		:param queue_save: Cola para enviar datos al proceso de guardado.
		:param queue_plot: Cola para enviar datos al proceso de plot.
		:param stop_event: Evento para detener el proceso.
		:param enable_save: Si True se activará los datos para guardar.
		:param enable_plot: Si True se activará el plot en tiempo real.
		:param enable_process: Si True se activará el procesamiento de los datos.
		"""
		super().__init__()
		self.queue_save = queue_save        # Fila para guardar los datos
		self.queue_plot = queue_plot        # Fila para plotar los datos
		self.queue_process = queue_process  # Fila para processar los datos
		self.stop_event = stop_event        # evento de los dtaos

		# Formato y parámetros de comunicación
		self.bin_msm_format = ">10Hc2c"     # Formato del mensaje binario    
		self.baudrate = 115200              # Velocidad de transmisión
		self.msm_size = struct.calcsize(    # El tamaño del mensaje es el 
			self.bin_msm_format             #   tamaño del struct más la 
			) + len(";****".encode())       #   longitud de la marca de fin

		# Lista de puertos Comm disponibles 
		self.ports = [port.device for port in list_ports.comports()]
		
		# Estas variables se inicializarán al abrir los puertos
		self.serial_connections = []        # Lista de conexiones seriales
		self.buffers = []                   # Buffer para cada conexión

		# Flags para activar el guardado y el plot
		self.enable_save = enable_save          # habilitar fila de guardado 
		self.enable_plot = enable_plot          # habilitar fila de plotadp
		self.enable_process = enable_process    # habilitar fila de procesado

		# Variable booleana compartida (tipo multiprocessing.Value)
		self.acquisition_active = acquisition_active # Monitorea la adquisición de datos

		# definir filtros para cada cuerpo
		self.filters = {i: LowPassFilter() for i in range(3)}

	def open_serial_ports(self):
		"""Abre los puertos serial disponibles y crea un buffer para cada uno."""
		ports_orig = self.ports.copy()          # Puertos aceptados
		self.ports = []                         # nuevos puertos
		self.serial_connections = []            # buffers para almecenamiento
		for port in ports_orig:                 # puertos disponibles
			try:                                  # intente abrir los puertos
				comm = serial.Serial(               #  abrir el puerto
					port=port,												#  puerto					
					baudrate=self.baudrate,						#  velocidad de transmisión
					parity=serial.PARITY_NONE,				#  paridad
					stopbits=serial.STOPBITS_ONE,			#  bits de parada
					bytesize=serial.EIGHTBITS,				#	tamaño de los bytes	
					timeout=0.1												#  tiempo de espera										
				)
				self.serial_connections.append(comm) 	#	añadir la conexión
				self.ports.append(port)								# añadir el puerto
				print(f"Puerto {port} abierto exitosamente.")
			except Exception as e:					# si no se puede abrir el puerto
				print(f"No se pudo abrir el puerto {port}: {e}")
		self.buffers = [bytearray() for _ in self.ports]

	def close_serial_ports(self):
		"""Cierra todas las conexiones serial."""
		for comm in self.serial_connections:		# para cada conexión
			comm.close()													# cerrar la conexión
			print(f"Puerto {comm.port} cerrado exitosamente.")

	def decode_serial_message(self, message):
		"""Decodifica el mensaje binario recibido."""
		value = struct.unpack(self.bin_msm_format, message)	# decodificar el mensaje
		return list(value[:10]), int(value[12])	# retornar los valores y el cuerpo

	def read_port_data(self, i):
		"""
		Lee datos del puerto i y busca el delimitador b';****' 
		para extraer un mensaje completo.
		"""
		comm = self.serial_connections[i]										# conexión serial
		data = comm.read(comm.in_waiting or self.msm_size)	# leer los datos
		self.buffers[i].extend(data)												# añadir los datos al buffer
		end = self.buffers[i].find(b";****")							# buscar el delimitador				
		values, body = None, None													# valores y cuerpo
		if end >= 0:																			# si se encuentra el delimitador
			message = self.buffers[i][:end]									# extraer el mensaje
			# Actualizamos el buffer eliminando el mensaje leído y el delimitador
			self.buffers[i] = self.buffers[i][end + len(b";****"):]	# actualizar el buffer
			if len(message) == self.msm_size - len(b";****"):	# si el mensaje tiene el tamaño correcto
				# decodificar el mensaje y retornar  los valores y el cuerpo
				return self.decode_serial_message(message)		
		return values, body	  # retornar los valores y el cuerpo como None

	def identify_comm_mfl(self):
		"""
		Identifica qué puerto corresponde a cada cuerpo leyendo mensajes 
		hasta obtener 3 identificaciones.Se espera que cada mensaje incluya en 
		el campo 'body' la identificación del cuerpo.
		"""
		port_to_body = {}					# diccionario de puerto a cuerpo
		max_attempts = 50					# número máximo de intentos
		self.open_serial_ports()	# abrir los puertos	

		while len(port_to_body) < 3:	# mientras no se identifiquen los 3 cuerpos
			for i in range(len(self.ports)):	# para cada puerto
				port = self.ports[i]						# puerto
				comm = self.serial_connections[i] # conexión
				# Si el puerto ya fue asignado, se omite
				if port in port_to_body.values(): 	# si el puerto ya fue asignado	
					continue													# continuar
				if len(port_to_body) >= 3:	# si ya se identificaron los 3 cuerpos
					break															# salir										
				attempts = 0								# intentos
				while attempts < max_attempts:    # mientras no se alcance el número máximo de intentos
					_ , body = self.read_port_data(i) # leer los datos del puerto
					if body is not None:					# si se identifica el cuerpo
						port_to_body[body] = port				# añadir el puerto al diccionario
						print(f"El puerto {port} corresponde al cuerpo {body + 1}")
						comm.close()										# cerrar la conexión
						break														# salir									
					attempts += 1									# incrementar los intentos
					if attempts == max_attempts and port not in port_to_body.values():
						print("No se pudo identificar un cuerpo para el puerto" + \
							f"{port} después de {max_attempts} intentos.")
			# Ordenamos los puertos según la identificación de cada cuerpo
			self.ports = [port_to_body[i] for i in sorted(port_to_body.keys())]
			print(f"Los puertos identificados en orden son {self.ports}")

	def publish_data_loop(self):
		"""
		Lee continuamente de los puertos, acumula datos y, cuando se tiene 
		suficiente, publica los datos en las colas para el guardado y el plot.
		"""
		# Informar que la adqiuisición está activa
		if self.acquisition_active is not None:
			self.acquisition_active.value = True

		n_ports = len(self.ports)				# número de puertos
		buffer_acquisition = {i: [] for i in range(n_ports)}	# buffer de adquisición
		buffer_plot = {i: [] for i in range(n_ports)}			# buffer de plot
		buffer_process = {i: [] for i in range(n_ports)}	# buffer de procesamiento
		
		#	Variables para el control de la publicación de datos
		n_it = 0												# número de iteraciones
		start_time_loop = time.time()		# tiempo de inicio del bucle

		# Reabrir los puertos para la adquisición
		self.open_serial_ports()				# abrir los puertos

		# Bucle principal de adquisición de datos
		while not self.stop_event.is_set():	# mientras no se reciba la señal de paro
			for i in range(n_ports):				# para cada puerto
				values, body = self.read_port_data(i)  # Leer datos de cada puerto
				if body is not None:					# si se identifica el cuerpo
					filtered_values = list(self.filters[body].apply(values) ) # Filtrar los datos
					# llenar las colas de datos paralelas
					buffer_acquisition[body].append(values)	# añadir los valores al buffer de adquisición
					if self.enable_plot.is_set():					# si se activa el plot
						buffer_plot[body].append(filtered_values)		# añadir los valores al buffer de plot
					if self.enable_process.is_set():			# si se activa el procesamiento
						buffer_process[body].append(filtered_values)	# añadir los valores al buffer de procesamiento

			self.queue_plot, buffer_plot, _ =  buffer_management( # manejar el buffer de plot 
				buffer_plot, self.enable_plot, self.queue_plot, 15)	#  con 10 datos

			self.queue_process, buffer_process, _ =  buffer_management(		# manejar el buffer de procesamiento
				buffer_process, self.enable_process, self.queue_process, 1)	# con 1 dato

			self.queue_save, buffer_acquisition, n_it =  buffer_management( # manejar el buffer de adquisición
				buffer_acquisition, self.enable_save, self.queue_save, 300,   # con 300 datos
				True, n_it, start_time_loop)																	# imprimir los datos

			time.sleep(0.001)													# esperar 1 ms
		else:	# si se recibe la señal de paro
			# Informar que la adquisición está inactiva
			if self.acquisition_active is not None:
				self.acquisition_active.value = False
		self.close_serial_ports()										# cerrar los puertos

	def run(self):
		"""
		Método principal del proceso: primero identifica los puertos asociados a cada cuerpo y luego
		inicia el bucle de publicación de datos.
		"""
		self.identify_comm_mfl()									# identificar los puertos
		self.publish_data_loop()									# publicar los datos

# =============================================================================
# Proceso de Guardado de Datos en CSV
# =============================================================================
class DataSaver(Process):
	def __init__(self, queue_save, run_event, name=""):
		""" 
		Proceso que guarda en un archivo CSV los datos que recibe de la cola.
		:param queue_save: Cola de datos a guardar.
		:param run_event: Evento para iniciar o detener el proceso.
		:param name: Nombre del archivo CSV. Si no se especifica, 
			se usará la fecha y hora actual.
		"""
		super().__init__()
		self.queue_save = queue_save
		self.run_event = run_event
		self.header_written = False
		self.writer = None
		self.csv_file = None
		self.name = name if len(name)==0 else "_" + name 

	def create_csv_file(self, num_bodies):
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S" + self.name)
		filename = f"datos_{timestamp}.csv"
		self.csv_file = open(filename, 'w', newline='')
		self.writer = csv.writer(self.csv_file)
		headers = []
		for body in range(num_bodies):
			for sensor in range(10):
				headers.append(f"b{body+1}_s{sensor}")
		self.writer.writerow(headers)
		self.header_written = True

	def run(self):
		while self.run_event.is_set():
			try:
				data = self.queue_save.get(timeout=0.5)
				if not self.header_written:
					num_bodies = len(data)
					self.create_csv_file(num_bodies)
				bodies = sorted(data.keys())
				array_list = []
				for body in bodies:
					body_data = np.array(data[body], dtype=np.uint16)
					array_list.append(body_data)
				data_array = np.concatenate(array_list, axis=1)
				csv_rows = data_array.tolist()
				self.writer.writerows(csv_rows)
				self.csv_file.flush()

			except Exception as e:
				print(f"Esperando datos para guardar... {e}")

# =============================================================================
# Proceso de Alarma de Datos
# =============================================================================
class DataAlarm(Process):
	def __init__(self, queue_alarm, run_event, threshold, alarms):
		"""
		Proceso que detecta alarmas en los datos recibidos y emite un sonido.
		:param queue_alarm: Cola de datos para procesar.
		:param run_event: Evento para iniciar o detener el proceso.
		:param threshold: Umbral para detectar alarmas.
		:param alarms: Diccionario de alarmas detectadas.
		"""
		super().__init__()						# inicializar la clase
		self.queue = queue_alarm			# cola de datos
		self.run_event = run_event		# evento de ejecución
		self.data = None							# datos
		self.threshold = threshold		# umbral
		self.alarms = alarms					# alarmas
		
	def run(self):
		""" Método principal del proceso. """		
		print("Alarm process is run ", self.run_event.is_set())
		# mientras el evento de ejecución esté activo
		while self.run_event.is_set():	
			current_threshold = self.threshold.value	# umbral actual
			try:												# intentar
				# Procesa todos los datos disponibles en la cola sin bloquear
				while not self.queue.empty(): # mientras la cola no esté vacía
					data = self.queue.get_nowait() # obtener los datos
					try:										# intentar 	tamaño (30,1)
						data_array = np.column_stack(	# concatenar los datos
							[np.array(data[key]) for key in sorted(data.keys())])
					except Exception as e:	# si hay un error 
						print(f"Error al concatenar datos: {e}")
						continue

					# matriz de datos (30, x)
					if self.data is None:	# si no hay datos
						self.data = data_array # asignar los datos
					else:			# si hay datos empezar a concatenar
						self.data = np.vstack((self.data, data_array))

					# 1. CONSTRUCCIÓN DE LA MUESTRA DE DATOS (30,20)
					sample_size = 20 						# tamaño de la muestra
					if len(self.data) > sample_size:		# si la muestra es mayor al tamaño
						self.data = self.data[-sample_size:, :] # reducir la muestra

 					# 2. PROCESAMIENTO DE LA MUESTRA SI ES SUFICIENTEMENTE GRANDE
					if len(self.data) >= sample_size:    # Si se tiene el tamaño nesario de la muestra
						# Convierte la muestra en un arreglo de NumPy para procesamiento
						rms = np.sqrt(np.mean(self.data ** 2, axis=0))  # Calcula el RMS de cada sensor
						ymax = np.max(self.data, axis=0)  # Encuentra los valores máximos de cada sensor

						# Identifica alarmas si los valores máximos exceden el umbral RMS + threshold
						eval_alarmas = ymax > (rms + current_threshold)	# evaluar las alarmas
						alarms = eval_alarmas*1												# convertir a 0 y 1
						alarms = alarms.reshape((len(alarms), 1))			# redimensionar
						self.alarms.update({		# separar las alarmas por cuerpo
								0: alarms[:10, :],	# actualizar las alarmas
								1: alarms[10:20],	
								2: alarms[20:]
						})
						# 3. ACCIÓN EN CASO DE ALARMA
						if any(eval_alarmas):  # Si se detecta una alarma		
							try:									# intentar 
								frequency = 2000  # Frecuencia del sonido de alarma en Hz
								duration = 800  # Duración del sonido en milisegundos
								winsound.Beep(frequency, duration)  # Genera el sonido
								# Reduce la muestra a la mitad para evitar alarmas repetitivas
								self.data = self.data[-10:]	# reducir la muestra
							except Exception as e:			# si hay un error
								print(f"Error al emitir alarma sonora: {e}")

			except Exception as e:		# si hay un error
				print(f"Error en update_plot: {e}")	# si hay un error

