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
from multiprocessing import Pool, Manager

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
    self.ports = [                      # Listar puertos seriales            
      port.device for port in self.ports]

    self.identify_comm_mfl()
    self.identify_comm_mfl()
    self.publish_data()

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
    while True:
      start_time_bucle = time.time()
      for i in range(n_ports):
        values, body = self.read_port_data(i)
        if body is not None and iterations:
          buffer_acquisition[body].append(values)
          
      iterations +=1
      if all(len(lst) >= 300 for lst in buffer_acquisition.values()):
        print("elapsed time : %.4f, Iterations %s =================" % (
          (time.time() - start_time), iterations- print_iteration))
        print_iteration = iterations
        for j, data in buffer_acquisition.items():
          buffer_acquisition[j] = buffer_acquisition[j][300:]
          print(f"para el cuerpot {j} el tamaño es {len(data)}")
            


if __name__ == "__main__":
  adquisition = DataAdquisition()



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
