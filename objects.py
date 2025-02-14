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
							enable_plot=Event(), enable_process=Event(), enable_save=Event()):
		""" Inicializa el proceso de adquisición de datos.
		:param queue_save: Cola para enviar datos al proceso de guardado.
		:param queue_plot: Cola para enviar datos al proceso de plot.
		:param stop_event: Evento para detener el proceso.
		:param enable_save: Si True se activará los datos para guarar.
		:param enable_plot: Si True se activará el plot en tiempo real."""
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

	def open_serial_ports(self):
		"""Abre los puertos serial disponibles y crea un buffer para cada uno."""
		ports_orig = self.ports.copy()          # Puertos aceptados
		self.ports = []                         # nuevos puertos
		self.serial_connections = []            # buffers para almecenamiento
		for port in ports_orig:                 # puertos disponibles
			try:                                  # intente abrir los puertos
				comm = serial.Serial(               # 
					port=port,
					baudrate=self.baudrate,
					parity=serial.PARITY_NONE,
					stopbits=serial.STOPBITS_ONE,
					bytesize=serial.EIGHTBITS,
					timeout=0.1
				)
				self.serial_connections.append(comm)
				self.ports.append(port)
				print(f"Puerto {port} abierto exitosamente.")
			except Exception as e:
				print(f"No se pudo abrir el puerto {port}: {e}")
		self.buffers = [bytearray() for _ in self.ports]

	def close_serial_ports(self):
		"""Cierra todas las conexiones serial."""
		for comm in self.serial_connections:
			comm.close()
			print(f"Puerto {comm.port} cerrado exitosamente.")

	def decode_serial_message(self, message):
		"""Decodifica el mensaje binario recibido."""
		value = struct.unpack(self.bin_msm_format, message)
		# Se retornan los 10 primeros valores y el valor entero del último campo (cuerpo)
		return list(value[:10]), int(value[12])

	def read_port_data(self, i):
		"""
		Lee datos del puerto i y busca el delimitador b';****' 
		para extraer un mensaje completo.
		"""
		comm = self.serial_connections[i]
		data = comm.read(comm.in_waiting or self.msm_size)
		self.buffers[i].extend(data)
		end = self.buffers[i].find(b";****")
		values, body = None, None
		if end >= 0:
			message = self.buffers[i][:end]
			# Actualizamos el buffer eliminando el mensaje leído 
			# y el delimitador
			self.buffers[i] = self.buffers[i][end + len(b";****"):]
			if len(message) == self.msm_size - len(b";****"):
				return self.decode_serial_message(message)
		return values, body

	def identify_comm_mfl(self):
		"""
		Identifica qué puerto corresponde a cada cuerpo leyendo mensajes 
		hasta obtener 3 identificaciones.Se espera que cada mensaje incluya en 
		el campo 'body' la identificación del cuerpo.
		"""
		port_to_body = {}
		max_attempts = 50
		self.open_serial_ports()

		while len(port_to_body) < 3:
			for i in range(len(self.ports)):
				port = self.ports[i]
				comm = self.serial_connections[i]
				# Si el puerto ya fue asignado, se omite
				if port in port_to_body.values():
					continue
				if len(port_to_body) >= 3:
					break
				attempts = 0
				while attempts < max_attempts:
					_ , body = self.read_port_data(i)
					if body is not None:
						port_to_body[body] = port
						print(f"El puerto {port} corresponde al cuerpo {body + 1}")
						comm.close()
						break
					attempts += 1
					if attempts == max_attempts and port not in port_to_body.values():
						print(f"No se pudo identificar un cuerpo para el puerto \
							{port} después de {max_attempts} intentos.")
			# Ordenamos los puertos según la identificación de cada cuerpo
			self.ports = [port_to_body[i] for i in sorted(port_to_body.keys())]
			print(f"Los puertos identificados en orden son {self.ports}")

	def publish_data_loop(self):
		"""
		Lee continuamente de los puertos, acumula datos y, cuando se tiene 
		suficiente, publica los datos en las colas para el guardado y el plot.
		"""
		n_ports = len(self.ports)
		buffer_acquisition = {i: [] for i in range(n_ports)}
		buffer_plot = {i: [] for i in range(n_ports)}
		buffer_process = {i: [] for i in range(n_ports)}
		
		n_it = 0
		start_time_loop = time.time()

		# Reabrir los puertos para la adquisición
		self.open_serial_ports()

		while not self.stop_event.is_set():
			for i in range(n_ports):
				values, body = self.read_port_data(i)
				# Leer datos de cada puerto
				if body is not None:
					# llenar las colas de datos paralelas
					buffer_acquisition[body].append(values)
					if self.enable_plot.is_set():
						buffer_plot[body].append(values)
					if self.enable_process.is_set():
						buffer_process[body].append(values)

			self.queue_plot, buffer_plot, _ =  buffer_management(
				buffer_plot, self.enable_plot, self.queue_plot, 10)
			#print(f"Tamaño de queue_plot: {self.queue_plot.qsize()}") 

			self.queue_process, buffer_process, _ =  buffer_management(
				buffer_process, self.enable_process, self.queue_process, 1)

			self.queue_save, buffer_acquisition, n_it =  buffer_management(
				buffer_acquisition, self.enable_save, self.queue_save, 300,
				True, n_it, start_time_loop)

			time.sleep(0.001)
		self.close_serial_ports()

	def run(self):
		"""
		Método principal del proceso: primero identifica los puertos asociados a cada cuerpo y luego
		inicia el bucle de publicación de datos.
		"""
		self.identify_comm_mfl()
		self.publish_data_loop()

# =============================================================================
# Proceso de Guardado de Datos en CSV
# =============================================================================
class DataSaver(Process):
	def __init__(self, queue_save, run_event, name=""):
		""" Proceso que guarda en un archivo CSV los datos que recibe de la cola.
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
		#if self.csv_file:
		#	self.csv_file.close()

# =============================================================================
# Proceso de Alarma de Datos
# =============================================================================
class DataAlarm(Process):
	def __init__(self, queue_alarm, run_event, threshold):
		super().__init__()
		self.queue = queue_alarm
		self.run_event = run_event
		self.data = None
		self.threshold = threshold
		
	def run(self):
		print("state data save", self.run_event.is_set())
		while self.run_event.is_set():
			current_threshold = self.threshold.value
			print(f"Alarm active, Thnreshokd {current_threshold}")
			try:
				# Procesa todos los datos disponibles en la cola sin bloquear
				while not self.queue.empty():
					data = self.queue.get_nowait()
					try:
						data_array = np.column_stack(
							[np.array(data[key]) for key in sorted(data.keys())])
					except Exception as e:
						print(f"Error al concatenar datos: {e}")
						continue

					if self.data is None:
						self.data = data_array
					else:
						self.data = np.vstack((self.data, data_array))

					# 1. CONSTRUCCIÓN DE LA MUESTRA DE DATOS
					sample_size = 20 
					if len(self.data) > sample_size:
						self.data = self.data[-sample_size:, :]

 					# 2. PROCESAMIENTO DE LA MUESTRA SI ES SUFICIENTEMENTE GRANDE
					if len(self.data) >= sample_size:    # Si se tiene el tamaño nesario de la 
						# Convierte la muestra en un arreglo de NumPy para procesamiento
						rms = np.sqrt(np.mean(self.data ** 2, axis=0))  # Calcula el RMS de cada sensor
						ymax = np.max(self.data, axis=0)  # Encuentra los valores máximos de cada sensor

						# Identifica alarmas si los valores máximos exceden el umbral RMS + threshold
						eval_alarmas = ymax > (rms + current_threshold)
						self.alarms = eval_alarmas*1

						# 3. ACCIÓN EN CASO DE ALARMA
						if any(eval_alarmas):  # Si se detecta una alarma
							try:
								frequency = 2000  # Frecuencia del sonido de alarma en Hz
								duration = 800  # Duración del sonido en milisegundos
								winsound.Beep(frequency, duration)  # Genera el sonido
								# Reduce la muestra a la mitad para evitar alarmas repetitivas
								self.data = self.data[-10:]
							except Exception as e:
								print(f"Error al emitir alarma sonora: {e}")

			except Exception as e:
				print(f"Error en update_plot: {e}")

# =============================================================================
# Bloque principal
# =============================================================================
#if __name__ == "__main__":
#	stop_event = Event()
#	# Para que Windows (y otros sistemas) puedan iniciar correctamente los procesos.
#	multiprocessing.freeze_support()
#
#	# Crear colas para compartir datos entre procesos
#	queue_save = Queue()
#	queue_plot = Queue()
#	queue_process = Queue()
#	threshold = 20
#
#	# Evento para señalizar el paro de todos los procesos
#	enable_plot=Event() 
#	enable_process=Event() 
#	enable_save=Event()
#	
#	#enable_plot.set()
#	enable_process.set()
#	#enable_save.set()
#
#	# Crear e iniciar los procesos
#	data_adquisition = DataAdquisition(queue_save, queue_plot, queue_process,
#										stop_event=stop_event,
#										enable_plot=enable_plot, 
#										enable_process=enable_process, 
#										enable_save=enable_save)
#	data_process = DataAlarm(queue_process, enable_process, threshold)
#	data_saver = DataSaver(queue_save, enable_save)
#
#	data_adquisition.start()
#	data_process.start()
#	#data_saver.start()
#
#	print("Procesos iniciados. Presiona Ctrl+C para detener.")
#
#	try:
#		while not stop_event.is_set():
#			time.sleep(0.003)
#	except KeyboardInterrupt:
#		print("Se recibió KeyboardInterrupt. Deteniendo procesos...")
#		stop_event.set()
#
#	# Esperar a que todos los procesos finalicen
#	data_adquisition.join()
#	data_saver.join()
#	data_plot.join()
#	print("Todos los procesos han finalizado.")
