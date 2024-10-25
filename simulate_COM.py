#%% ========================================================================
# import libraries
# ==========================================================================
'''Script con algunas funciones para ge
generar datos simuados con las caracteristicas del MFL y enviarlos a un puerto 
COM

 '''
import serial   # para la comunicación con puertos seriales.
import time     # para manejar tiempos y demoras.
import random   # para generar valores aleatorios.
import struct


#%% ========================================================================
# Función para generar datos simulados
# ==========================================================================
def generate_simulated_data():
  '''
  Genera una cadena de datos simulados según el formato '>10Hc2c'.
  
  La cadena comienza con una secuencia de inicio '****' y termina con un
  carácter de fin ';'. Entre estas secuencias, se generan valores hexadecimales
  que simulan la estructura de datos '>10Hc2c':
  
  - 10 valores hexadecimales de 16 bits (2 bytes).
  - 1 valor hexadecimal de 8 bits (1 byte).
  - 2 valores hexadecimales de 8 bits (1 byte cada uno).

  Returns: str: La cadena de datos simulados.
  '''
  
  start_sequence = '****'     # Inicio de la trama de datos
  end_sequence = ';'          # Fin de la trama de datos
  separator = ':'             # separador para identificar el sensor
  
  # Generar los 10 primeros valores hexadecimales de 16 bits (2 bytes)
  hex_data = struct.pack('>10H', *[random.randint(0, 4096) for _ in range(10)])
  # Generar 2 valores hexadecimales de 8 bits (1 byte cada uno)
  c_data = struct.pack('>2B', *[random.randint(0, 3) for _ in range(2)])
  
  # Construir la cadena de datos combinando las partes generadas n
  simulated_data = f'{start_sequence}{hex_data}{separator}{c_data}{end_sequence}'
  
  return simulated_data  # Devolver la cadena de datos simulados

#%% ========================================================================
# Simulación de puerto serial, imprimiendo datos simulados en tiempo real
# ==========================================================================
def simulate_serial_port():
  '''
  Simula la recepción de datos desde un puerto serial imprimiendo los datos 
  generados en tiempo real.

  En un bucle infinito, genera datos simulados utilizando la función 
  `generate_simulated_data()` y los imprime, manteniendo una frecuencia de 
  muestreo de aproximadamente 335 Hz.
  '''
  
  while True:
    simulated_data = generate_simulated_data()  # Generar datos simulados
    print(f"Datos recibidos: {simulated_data}") # Imprimir datos simulados 

    # Esperar un tiempo para mantener la frecuencia de muestreo (335 Hz)
    time.sleep(1 / 335)  

#%% ========================================================================
# Función para recolectar datos durante un tiempo determinado
# ==========================================================================
def collect_data(duration):
  '''
  Recolecta datos simulados durante un periodo de tiempo especificado.

  Esta función recoge los datos generados durante la duración indicada y los 
  almacena en una lista. La frecuencia de muestreo se mantiene a 
  aproximadamente 335 Hz.
  
  Args: duration (float): Duración en segundos durante la cual se recogerán 
    los datos.

  Returns: list: Lista de cadenas de datos simulados recogidos durante 
    el periodo.
  '''
    
  start_time = time.time()  # Capturar el tiempo de inicio
  data_list = []            # Lista para almacenar los datos
  
  # Recolectar datos hasta que transcurra el tiempo especificado
  while (time.time() - start_time) < duration:
    simulated_data = generate_simulated_data()  # Generar un nuevo dato simulado
    data_list.append(simulated_data)            # Añadir el dato a la lista
    
    time.sleep(1 / 335) # Esperar  para mantener frecuencia de muestreo (335 Hz)
    
  return data_list  # Devolver la lista de datos recolectados


#%% ========================================================================
# Función enviar datos a un puerto COM
# ==========================================================================
#def send_data_to_com_port(port, baudrate=115200):
#  '''Envía datos simulados a un puerto COM en tiempo real.'''
#  with serial.Serial(port, baudrate) as ser:
#    while True:
#      data = generate_simulated_data()
#      ser.write(data.encode())  # Enviar los datos codificados como bytes
#      time.sleep(1 / 335)  # Frecuencia de muestreo de 300 Hz
def send_data_to_com_port(port, baudrate=115200):
  '''Envía datos simulados a un puerto COM en tiempo real.'''
  with serial.Serial(port, baudrate) as ser:
    while True:
      data = generate_simulated_data()
      ser.write(data)  # Enviar los datos en formato binario
      time.sleep(1 / 335)  # Frecuencia de muestreo de aproximadamente 335 Hz


#%% ========================================================================
# Configuración de duración para la recolección de datos
# ==========================================================================
#duration = 1  # Duración en segundos para la recolección de datos
##
#collected_data = collect_data(duration)   # recolectar datos 
#
#print(f"Datos recogidos durante {duration} segundo(s):")
#for data in collected_data:               # Mostrar los datos recolectados
#    #data_print =  struct.unpack(">10Hc2c", data)
#    print(data)               # Imprimir cada dato de la lista recolectada

