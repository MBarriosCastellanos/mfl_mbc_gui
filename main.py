#%% Importar librerías
import serial
import struct
import csv
from datetime import datetime
import numpy as np
from serial.tools import list_ports
import time
import threading                  # Hilos de ejecución
import queue                      # Cola de datos
import matplotlib.pyplot as plt    # Gráficos
from matplotlib.animation import FuncAnimation

#%% Definir constantes
start_time = time.time()
save = True                     # Guardar datos en un archivo CSV
plot = True                     # Mostrar gráficos en tiempo real

#%%

#%% Adquisición de datos
class DataAdquisition:
  def __init__(self):
    self.bin_msm_format = ">10Hc2c"         # Formato de mensaje binario
    self.baudrate = 115200                  # Velocidad de transmisión
    self.msm_size = struct.calcsize(        # Tamaño del mensaje
      self.bin_msm_format) + len(";****".encode())

    # Identificación de los puertos seriales
    self.ports = [                                
      port.device for port in list_ports.comports()]

    # 
    self.data_queue_plot = queue.Queue()         # Cola de datos
    self.data_queue_save = queue.Queue()         # Cola de datos
    self.running = False                    # Bandera de ejecución
    self.thread = None                      # Hilo de ejecución

    self.buffer_publish = {}                # Buffer de datos a publicar

    
    self.save_active = False  # Bandera para indicar si el guardado está activo
    self.plot_active = False  # Bandera para indicar si el guardado está activo

    self.identify_comm_mfl()
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

  def set_save_active(self, active):
    self.save_active = active
    print(f"Guardado activo: {active}")  

  def set_plot_active(self, active):
    self.plot_active = active
    print(f"Plotado activo: {active}")  

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

      min_len = min(len(lst) for lst in buffer_acquisition.values())
      if min_len % 10 == 0 and min_len >= 10 and self.plot_active:
        self.data_queue_plot.put(buffer_acquisition)
          
      iterations +=1
      if min_len >= 300:
        print("elapsed time : %.4f, Iterations %s =================" % (
          (time.time() - start_time), iterations- print_iteration))
        print_iteration = iterations
        for j, data in buffer_acquisition.items():
          self.buffer_publish[j] = data[:300]
          buffer_acquisition[j] = data[300:]
          print(f"para el cuerpo {j} el tamaño es {len(data)}")
        if self.save_active:
          self.data_queue_save.put(self.buffer_publish)

class DataSaver:
  def __init__(self, data_adquisition):
    self.data_adquisition = data_adquisition            # Adquisición de datos
    self.running = False                                # Bandera de ejecución
    self.writer = None                        # Escritor de archivo CSV
    self.thread = None                        # Hilo de ejecución
    self.header_written = False               # Bandera de encabezado escrito
    self.thread = threading.Thread(                     # Hilo de ejecución
      target=self.run)

  def start(self):
    self.running = True                       # Iniciar ejecución
    self.data_adquisition.set_save_active(True)  # Activar guardado
    self.thread.start()                       # Iniciar hilo de ejecución
    print("DataSaver iniciado.")

  def stop(self):
    self.running = False                      # Detener ejecución
    self.thread.join()                        # Esperar a que termine
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
    while self.running:
      try:
        # Adquirir datos de la cola un tiempo de espera de 0.5 segundos
        data = self.data_adquisition.data_queue_save.get(timeout=0.5)

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

class DataPlot:
  def __init__(self, data_adquisition):
    self.data_adquisition = data_adquisition            # Adquisición de datos
    self.running = False                                # Bandera de ejecución
    self.writer = None                        # Escritor de archivo CSV
    self.thread = None                        # Hilo de ejecución
    self.header_written = False               # Bandera de encabezado escrito
    self.thread = threading.Thread(                     # Hilo de ejecución
      target=self.run)
    self.csv_file = None                                # Archivo CSV
    self.data = None                                    # Datos

    # Configuración de la figura y líneas
    self.fig, self.ax = plt.subplots(3, 1, figsize=(10, 10))
    self.lines = []
    
    # Crear 10 líneas por cada subplot (una por sensor)
    for i in range(3):
      body_lines = [self.ax[i].plot([], [], lw=1)[0] for _ in range(10)]
      self.lines.append(body_lines)
      self.ax[i].set_title(f"Body {i+1}")
      #self.ax[i].set_xlim(0, 3000)
      #self.ax[i].set_ylim(0, 1024)  # Ajusta según tu rango de datos
    
    # Animación
    self.ani = FuncAnimation(
        self.fig, 
        self.update_plot, 
        interval=100, 
        blit=True, 
        cache_frame_data=False
    )

  def start(self):
    self.running = True                       # Iniciar ejecución
    self.data_adquisition.set_plot_active(True)  # Activar guardado
    self.thread.start()                       # Iniciar hilo de ejecución
    print("DataPlot iniciado.")
    plt.show()  # Mostrar la ventana en el hilo principal

  def stop(self):
    self.running = False                      # Detener ejecución
    self.thread.join()                        # Esperar a que termine
    if self.csv_file is not None:             # Si el archivo existe
      self.close_csv.close()                  # Cerrar archivo CSV
    print("DataPlot detenido.")

  def run(self):
    while self.running:
      try:
        # Adquirir datos de la cola un tiempo de espera de 0.5 segundos
        data = self.data_adquisition.data_queue_plot.get(timeout=0.5)
        data_array = np.column_stack([
          np.array(data[key])[-10:] for key in sorted(data.keys())
        ])

        # Si es la primera iteración, inicializar self.data
        if self.data is None:
          self.data = data_array
        else:
          # Añadir la nueva fila al final de self.data
          self.data = np.vstack((self.data, data_array))

        # Verificar el tamaño de self.data
        if len(self.data) >= 3000:
          # Eliminar las primeras 10 filas
          self.data = self.data[10:]

        # plotar los datos en tiempo real
        for i in range(3):
          self.ax[i].clear()
          self.ax[i].plot(self.data[:, i*10:(i+1)*10])
          self.ax[i].set_title(f"Body {i + 1}")

      except queue.Empty:
        continue

  def update_plot(self, frame):
    if self.data is not None and len(self.data) > 0:
      # Actualizar todas las líneas
      for body in range(3):
        for sensor in range(10):
          col = body * 10 + sensor
          x_data = np.arange(len(self.data))
          y_data = self.data[:, col]
          
          self.lines[body][sensor].set_data(x_data, y_data)

      # Ajustar límites dinámicamente
      for ax in self.ax:
          ax.set_xlim(0, len(self.data))
      
    return [line for sublist in self.lines for line in sublist]

if __name__ == "__main__":
  adquisition = DataAdquisition()
  data_saver = DataSaver(adquisition)
  data_saver.start()
  data_plot = DataPlot(adquisition)
  data_plot.start()

  try:
    while True:
      time.sleep(0.001)
  except KeyboardInterrupt:
    adquisition.stop()
    data_saver.stop()
    data_plot.stop()
