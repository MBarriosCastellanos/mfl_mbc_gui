#%% Importar librerías
import serial
import struct
import csv
from datetime import datetime
import numpy as np
from serial.tools import list_ports
import time
import matplotlib.pyplot as plt
import subprocess
import os
import multiprocessing

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
    self.ports = list_ports.comports()  # Puertos seriales disponibles
    self.ports = [                      # ìstar puertos seriales            
      port.device for port in self.ports]

    self.identify_comm_mfl()
    self.identify_comm_mfl()


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

  def close_serial_ports(self):
    for comm in self.serial_connections:
      comm.close()
      print(f"Puerto {comm.port} cerrado exitosamente.")

  def read_serial_data(self, comm, buffer):
    data = comm.read(comm.in_waiting or self.msm_size) # Leer datos
    buffer.extend(data)                     # Agregar datos al buffer
    end = buffer.find(b";****")             # Buscar fin de línea
    if end >= 0:                            # Si se encontró el fin de línea
      message = buffer[:end]                # Extraer mensaje
      buffer = buffer[end + len(b";****"):] # Actualizar buffer
      if len(message) == self.msm_size - len(b";****"): # Verificar tamaño del mensaje
        values, body = self.decode_serial_message(message) # Decodificar mensaje
      else:
        values, body = None, None
    else:
      values, body = None, None 
    return buffer, values, body

  def identify_comm_mfl(self):
    # Paso 1: Identificar qué puerto corresponde a cada cuerpo
    port_to_body = {}
    max_attempts = 50  # Máximo número de intentos por puerto 

    self.open_serial_ports()

    # Mientras no se hayan identificado los 3 cuerpos
    while len(port_to_body) < 3:
      for port, comm in zip(self.ports, self.serial_connections):
        if port in port_to_body.values():
          continue
        attempts = 0
        buffer = bytearray()
        while attempts < max_attempts:
          buffer, _ , body = self.read_serial_data(comm, buffer)
          if body is not None:
            port_to_body[body] = port
            print(f"El puerto {port} corresponde al cuerpo {body + 1}")
            comm.close()
            break
          attempts += 1 
          if attempts == max_attempts and port not in port_to_body.values():
            print(f"No se pudo identificar un cuerpo para el puerto {port} después de {max_attempts} intentos.")
    self.ports = [port_to_body[i] for i in sorted(port_to_body.keys())]
    print(f"Los puertos identificados en orden son {self.ports}")

  def publish_data(self):
    self.open_serial_ports()
    buffers = [bytearray() for _ in self.serial_connections]
    buffer_acquisition = {0: [], 1: [], 2: []}
    iterations = 0

    try:
      while True:
        for i, comm  in enumerate(self.serial_connections):
          buffers[i], values, body = self.read_serial_data(comm, buffers[i])
          if body is not None and iterations>600:
            buffer_acquisition[body].append(values)
        iterations +=1
        if iterations % 300 == 0:
          print("elapsed time : %.4f =================" % (time.time() - start_time))
          for i in buffer_acquisition:
            size = np.shape(np.array(buffer_acquisition[i]))
            print(f"Se leyeron {size} datos del cuerpo {i}")
    except KeyboardInterrupt:
      self.close_serial_ports()
      print(f"Se leyeron {iterations} iteraciones de datos.")
      pass

if __name__ == "__main__":
  adquisition = DataAdquisition()
  adquisition.publish_data()



  #acquisition_queue = multiprocessing.Queue()
  #save_queue = multiprocessing.Queue()

  #data_acquisition = DataAcquisition(acquisition_queue)
  #data_saver = DataSaver(save_queue)
  #data_plotter = DataPlotter(acquisition_queue)
  #
  #acquisition_process = multiprocessing.Process(target=data_acquisition.start)
  #saver_process = multiprocessing.Process(target=data_saver.start)
  #plotter_process = multiprocessing.Process(target=data_plotter.start)
  #
  #acquisition_process.start()
  #saver_process.start()
  #plotter_process.start()
  #
  #acquisition_process.join()
  #saver_process.join()
  #plotter_process.join()
