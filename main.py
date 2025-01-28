#%% Importar librerías
import serial
import struct
import csv
from datetime import datetime
import numpy as np
from serial.tools import list_ports
import time
import threading
import queue

#%% Definir constantes
start_time = time.time()
save = True                     # Guardar datos en un archivo CSV
plot = True                     # Mostrar gráficos en tiempo real

#%% Adquisición de datos
class DataAdquisition:
  def __init__(self):
    self.bin_msm_format = ">10Hc2c"         # Formato de mensaje binario
    self.baudrate = 115200                  # Velocidad de transmisión
    self.msm_size = struct.calcsize(        # Tamaño del mensaje
      self.bin_msm_format) + len(";****".encode())
    self.ports = [                      # Puertos seriales disponibles           
      port.device for port in list_ports.comports()]
    self.data_queue = queue.Queue()         # Cola de datos
    self.running = False                    # Bandera de ejecución
    self.thread = None                      # Hilo de ejecución
    self.buffer_publish = {}                # Buffer de datos a publicar

    self.identify_comm_mfl()
    #self.identify_comm_mfl()
    self.start()

  def start(self):
    self.running = True                     # Iniciar ejecución
    self.thread = threading.Thread(         # Crear hilo de ejecución
      target=self.publish_data)
    self.thread.start()                     # Iniciar hilo de ejecución
  
  def stop(self):
    self.running = False                    # Detener ejecución
    if self.thread is not None:             # Si el hilo existe
      self.thread.join()                    # Esperar a que termine
    self.close_serial_ports()               # Cerrar puertos seriales

  def decode_serial_message(self, message):
    value = struct.unpack(                  # Decodificar mensaje
      self.bin_msm_format, message)
    return list(value[:10]), int(value[12]) # retornar valores, cuerpo
  
  def open_serial_ports(self):
    ports = self.ports

    self.ports = []
    self.serial_connections = []               # Lista de conexiones seriales
        
    for port in ports:
      try:
        comm = serial.Serial(             # Crear conexión 
          port=port,                      # Puerto
          baudrate=self.baudrate,       # Velocidad de transmisión
          parity=serial.PARITY_NONE,    # Paridad de bits 
          stopbits=serial.STOPBITS_ONE, # Bits de parada (units of stopbits)
          bytesize=serial.EIGHTBITS,    # Bits de datos ()
          timeout=0.1                   # Tiempo de espera en segundos
        )
        self.serial_connections.append(comm) # Agregar conexión a la lista
        self.ports.append(port)              # Agregar puerto a la lista
        print(f"Puerto {port} abierto exitosamente.")
      except Exception as e:          # Manejar excepción
        print(f"No se pudo abrir el puerto {port}: {e}")  
    self.buffers = [bytearray() for _ in self.ports]

  def close_serial_ports(self):
    for comm in self.serial_connections:
      comm.close()
      print(f"Puerto {comm.port} cerrado exitosamente.")

  def read_port_data(self, i):
    comm = self.serial_connections[i]
    data = comm.read(comm.in_waiting or self.msm_size) # Leer datos
    self.buffers[i].extend(data)                     # Agregar datos al buffer
    end = self.buffers[i].find(b";****")             # Buscar fin de línea
    values, body = None, None
    if end >= 0:                            # Si se encontró el fin de línea
      message = self.buffers[i][:end]                # Extraer mensaje
      self.buffers[i] = self.buffers[i][end + len(b";****"):] # Actualizar buffer
      if len(message) == self.msm_size - len(b";****"): # Verificar tamaño del mensaje
        return self.decode_serial_message(message) # Decodificar mensaje
    return values, body

  def identify_comm_mfl(self):
    # Paso 1: Identificar qué puerto corresponde a cada cuerpo
    port_to_body = {}
    max_attempts = 50  # Máximo número de intentos por puerto 

    self.open_serial_ports()

    # Mientras no se hayan identificado los 3 cuerpos
    while len(port_to_body) < 3:
      for i in range(len(self.ports)):
        port = self.ports[i]
        comm = self.serial_connections[i]
        if port in port_to_body.values():
          continue
        if len(port_to_body)>=3:
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
            print(f"No se pudo identificar un cuerpo para el puerto\
               {port} después de {max_attempts} intentos.")
    self.ports = [port_to_body[i] for i in sorted(port_to_body.keys())]
    print(f"Los puertos identificados en orden son {self.ports}")

  def publish_data(self):
    self.open_serial_ports()
    n_ports = len(self.ports)
    buffer_acquisition = {i: [] for i in range(n_ports)}
    iterations = 0
    print_iteration = 0
    self.buffer_publish = {i: [] for i in range(n_ports)}
    while self.running:
      start_time_bucle = time.time()
      for i in range(n_ports):
        values, body = self.read_port_data(i)
        if body is not None :
          buffer_acquisition[body].append(values)
          
      iterations +=1
      if all(len(lst) >= 300 for lst in buffer_acquisition.values()):
        print("elapsed time : %.4f, Iterations %s =================" % (
          (time.time() - start_time), iterations- print_iteration))
        print_iteration = iterations
        for j, data in buffer_acquisition.items():
          self.buffer_publish[j] = data[:300]
          buffer_acquisition[j] = data[300:]
          print(f"para el cuerpo {j} el tamaño es {len(data)}")
        self.data_queue.put(self.buffer_publish)
class DataSaver:
  def __init__(self, data_adquisition):
    self.data_adquisition = data_adquisition            # Adquisición de datos
    self.running = False                                # Bandera de ejecución
    self.csv_file = None                                # Archivo CSV
    self.writer = None                        # Escritor de archivo CSV
    self.thread = None                        # Hilo de ejecución
    self.header_written = False               # Bandera de encabezado escrito
    self.thread = threading.Thread(                     # Hilo de ejecución
      target=self.run)
  def start(self):
    self.running = True                       # Iniciar ejecución
    self.thread.start()                       # Iniciar hilo de ejecución
    print("DataSaver iniciado.")

  def stop(self):
    self.running = False                      # Detener ejecución
    self.thread.join()                        # Esperar a que termine
    if self.csv_file is not None:             # Si el archivo existe
      self.close_csv.close()                  # Cerrar archivo CSV
    print("DataSaver detenido.")

  def create_csv_file(self, num_bodies):
    timestamp = datetime.now(                 # fecha horas minutos
      ).strftime("%Y%m%d_%H%M%S")
    filename = f"datos_{timestamp}.csv"       # nombre del archivo
    self.csv_file =  open(filename, 'w', newline='')
    self.writer = csv.writer(self.csv_file)
    # crear encabezado
    headers = []
    for body in range(num_bodies):            # Número de cuerpos
      for sensor in range(10):              # Número de sensores
        headers.append(f"b{body+1}_s{sensor}")  # Nombre de la columna
    self.writer.writerow(headers)            # Escribir encabezado
    self.header_written = True           # Bandera de encabezado escrito

  def run(self):
    num_bodies = None
    while self.running:
      try:
        data = self.data_adquisition.data_queue.get(timeout=0.1)

        if not self.header_written:
          num_bodies = len(data)            # Número de cuerpos
          self.create_csv_file(num_bodies)  # Crear archivo CSV

        # convertir a numpy array
        bodies = sorted(data.keys())        # Cuerpos
        array_list = []                     # Lista de arrays

        for body in bodies:                 # Para cada cuerpo
          body_data = np.array(             # Crear array
            data[body], dtype=np.uint16)
          array_list.append(body_data)      # Agregar array a la lista

        # concatenar arrays
        data_array = np.concatenate(array_list, axis=1)

        # convertir a lista de listas para CSV
        csv_rows = data_array.tolist()

        # escribir en archivo CSV
        self.writer.writerows(csv_rows)     # Escribir filas en archivo CSV
        self.csv_file.flush()               # Limpiar buffer

      except queue.Empty:
        continue
        
if __name__ == "__main__":
  adquisition = DataAdquisition()
  data_saver = DataSaver(adquisition)
  data_saver.start()

  try:
    while True:
      time.sleep(0.1)
  except KeyboardInterrupt:
    adquisition.stop()
    data_saver.stop()



# %%
