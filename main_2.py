#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implementación de la adquisición, guardado y plot usando multiprocessing.
"""

import serial
import struct
import csv
from datetime import datetime
import numpy as np
from serial.tools import list_ports
import time
import matplotlib.pyplot as plt

# Importamos las herramientas de multiprocessing y la excepción Empty
import multiprocessing
from multiprocessing import Process, Queue, Event
from queue import Empty  # Para capturar la excepción en get(timeout=...)
from matplotlib.animation import FuncAnimation

# =============================================================================
# Proceso de Adquisición de Datos
# =============================================================================
class DataAdquisition(Process):
    def __init__(self, queue_save, queue_plot, stop_event, enable_save=True, enable_plot=True):
        """
        Inicializa el proceso de adquisición de datos.
        :param queue_save: Cola para enviar datos al proceso de guardado.
        :param queue_plot: Cola para enviar datos al proceso de plot.
        :param stop_event: Evento para detener el proceso.
        :param enable_save: Si True se activará el guardado.
        :param enable_plot: Si True se activará el plot en tiempo real.
        """
        super().__init__()
        self.queue_save = queue_save
        self.queue_plot = queue_plot
        self.stop_event = stop_event

        # Formato y parámetros de comunicación
        self.bin_msm_format = ">10Hc2c"
        self.baudrate = 115200
        self.msm_size = struct.calcsize(self.bin_msm_format) + len(";****".encode())

        # Lista de puertos disponibles (se identificará posteriormente cuál corresponde a cada cuerpo)
        self.ports = [port.device for port in list_ports.comports()]
        
        # Estas variables se inicializarán al abrir los puertos
        self.serial_connections = []
        self.buffers = []

        # Flags para activar el guardado y el plot
        self.enable_save = enable_save
        self.enable_plot = enable_plot

    def open_serial_ports(self):
        """Abre los puertos serial disponibles y crea un buffer para cada uno."""
        ports_orig = self.ports.copy()
        self.ports = []
        self.serial_connections = []
        for port in ports_orig:
            try:
                comm = serial.Serial(
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
            try:
                comm.close()
                print(f"Puerto {comm.port} cerrado exitosamente.")
            except Exception as e:
                print(f"Error al cerrar el puerto {comm.port}: {e}")

    def decode_serial_message(self, message):
        """Decodifica el mensaje binario recibido."""
        value = struct.unpack(self.bin_msm_format, message)
        # Se retornan los 10 primeros valores y el valor entero del último campo (cuerpo)
        return list(value[:10]), int(value[12])

    def read_port_data(self, i):
        """
        Lee datos del puerto i y busca el delimitador b';****' para extraer un mensaje completo.
        """
        comm = self.serial_connections[i]
        data = comm.read(comm.in_waiting or self.msm_size)
        self.buffers[i].extend(data)
        end = self.buffers[i].find(b";****")
        values, body = None, None
        if end >= 0:
            message = self.buffers[i][:end]
            # Actualizamos el buffer eliminando el mensaje leído y el delimitador
            self.buffers[i] = self.buffers[i][end + len(b";****"):]
            if len(message) == self.msm_size - len(b";****"):
                return self.decode_serial_message(message)
        return values, body

    def identify_comm_mfl(self):
        """
        Identifica qué puerto corresponde a cada cuerpo leyendo mensajes hasta obtener 3 identificaciones.
        Se espera que cada mensaje incluya en el campo 'body' la identificación del cuerpo.
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
                        print(f"No se pudo identificar un cuerpo para el puerto {port} después de {max_attempts} intentos.")
        # Ordenamos los puertos según la identificación de cada cuerpo
        self.ports = [port_to_body[i] for i in sorted(port_to_body.keys())]
        print(f"Los puertos identificados en orden son {self.ports}")

    def publish_data_loop(self):
        """
        Lee continuamente de los puertos, acumula datos y, cuando se tiene suficiente, publica
        los datos en las colas para el guardado y el plot.
        """
        n_ports = len(self.ports)
        buffer_acquisition = {i: [] for i in range(n_ports)}
        buffer_plot = {i: [] for i in range(n_ports)}
        iterations = 0
        print_iteration = 0
        start_time_loop = time.time()

        # Reabrir los puertos para la adquisición
        self.open_serial_ports()

        while not self.stop_event.is_set():
            for i in range(n_ports):
                values, body = self.read_port_data(i)
                if body is not None:
                    # Se asume que 'body' es un entero entre 0 y n_ports-1
                    buffer_acquisition[body].append(values)
                    if self.enable_plot:
                        buffer_plot[body].append(values)

            # Si existen datos en todos los buffers, se determina el mínimo
            if buffer_acquisition:
                min_len = min(len(lst) for lst in buffer_acquisition.values())
            else:
                min_len = 0

            # Si existen datos en todos los buffers, se determina el mínimo
            if buffer_plot:
                min_len_p = min(len(lst) for lst in buffer_plot.values())
            else:
                min_len_p = 0

            if min_len_p >= 10:
                buffer_publish = {}
                for j, data in buffer_plot.items():
                    buffer_publish[j] = data[:10]
                    buffer_plot[j] = data[10:]
                if self.enable_plot:
                    self.queue_plot.put(buffer_publish)                

            # Si se han acumulado suficientes datos, se envían a la cola de plot
            #if min_len % 10 == 0 and min_len >= 10 and self.enable_plot:
            #    # Se envía una copia del buffer (para evitar condiciones de carrera)
            #    self.queue_plot.put(buffer_acquisition.copy())

            iterations += 1
            if min_len >= 300:
                elapsed = time.time() - start_time_loop
                print("elapsed time : %.4f, Iterations %s =================" % (elapsed, iterations - print_iteration))
                print_iteration = iterations
                buffer_publish = {}
                for j, data in buffer_acquisition.items():
                    buffer_publish[j] = data[:300]
                    buffer_acquisition[j] = data[300:]
                    print(f"Para el cuerpo {j} el tamaño es {len(data)}")
                if self.enable_save:
                    self.queue_save.put(buffer_publish)
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
    def __init__(self, queue_save, stop_event):
        """
        Proceso que guarda en un archivo CSV los datos que recibe de la cola.
        """
        super().__init__()
        self.queue_save = queue_save
        self.stop_event = stop_event
        self.header_written = False
        self.writer = None
        self.csv_file = None

    def create_csv_file(self, num_bodies):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
        while not self.stop_event.is_set():
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
            except Empty:
                continue
            except Exception as e:
                print(f"Error en DataSaver: {e}")
        if self.csv_file:
            self.csv_file.close()


# =============================================================================
# Proceso de Plot de Datos
# =============================================================================
class DataPlot(Process):
    def __init__(self, queue_plot, stop_event):
        """
        Proceso que genera gráficos en tiempo real a partir de los datos recibidos.
        """
        super().__init__()
        self.queue_plot = queue_plot
        self.stop_event = stop_event
        self.data = None

    def run(self):
        #plt.ion()  # Modo interactivo
        fig, ax = plt.subplots()  # Aquí se define 'fig' y 'ax'
        ax.set_xlim(0, 3000)
        ax.set_ylim(2250, 2500)
        
        # Crea las líneas (suponiendo que self.data ya se haya inicializado o se defina aquí)
        lines = []  # Lista para almacenar las líneas de cada sensor
        if self.data is not None:
            num_lines = self.data.shape[1]
        else:
            # Si aún no hay datos, asume un número de líneas (por ejemplo, 4 sensores)
            num_lines = 30
        for i in range(num_lines):
            line, = ax.plot([], [], lw=1, label=f"Sensor {i+1}")
            lines.append(line)
        ax.legend()

        def update_plot(frame):
            try:
                # Procesa todos los datos disponibles en la cola sin bloquear
                while not self.queue_plot.empty():
                    data = self.queue_plot.get_nowait()
                    try:
                        data_array = np.column_stack([np.array(data[key])[-10:] for key in sorted(data.keys())])
                    except Exception as e:
                        print(f"Error al concatenar datos: {e}")
                        continue

                    if self.data is None:
                        self.data = data_array
                    else:
                        self.data = np.vstack((self.data, data_array))
                    if len(self.data) > 3000:
                        self.data = self.data[10:]
            except Exception as e:
                print(f"Error en update_plot: {e}")

            if self.data is not None:
                x_data = np.arange(len(self.data))
                for i, line in enumerate(lines):
                    line.set_data(x_data, self.data[:, i])
            return lines  # Importante para blitting

        ani = FuncAnimation(fig, update_plot, interval=33, cache_frame_data=True)
        plt.show()

# =============================================================================
# Bloque principal
# =============================================================================
if __name__ == "__main__":
    # Para que Windows (y otros sistemas) puedan iniciar correctamente los procesos.
    multiprocessing.freeze_support()

    # Crear colas para compartir datos entre procesos
    queue_save = Queue()
    queue_plot = Queue()
    # Evento para señalizar el paro de todos los procesos
    stop_event = Event()

    # Crear e iniciar los procesos
    data_adquisition = DataAdquisition(queue_save, queue_plot, stop_event, enable_save=True, enable_plot=True)
    data_saver = DataSaver(queue_save, stop_event)
    data_plot = DataPlot(queue_plot, stop_event)

    data_adquisition.start()
    data_saver.start()
    data_plot.start()

    print("Procesos iniciados. Presiona Ctrl+C para detener.")

    try:
        while not stop_event.is_set():
            time.sleep(0.003)
    except KeyboardInterrupt:
        print("Se recibió KeyboardInterrupt. Deteniendo procesos...")
        stop_event.set()

    # Esperar a que todos los procesos finalicen
    data_adquisition.join()
    data_saver.join()
    data_plot.join()
    print("Todos los procesos han finalizado.")
