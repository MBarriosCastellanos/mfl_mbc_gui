#%% Importar librerías
import serial
import struct
import csv
from datetime import datetime
import numpy as np
from serial.tools import list_ports
import time
from multiprocessing import Process, Queue
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

#%% Definir constantes
save = True                     # Guardar datos en un archivo CSV
plot = True                     # Mostrar gráficos en tiempo real

#%% Clase de Adquisición de Datos usando multiprocessing
class DataAdquisition:
    def __init__(self, queue_save, queue_plot):
        self.queue_save = queue_save         # Cola para enviar datos al guardador
        self.queue_plot = queue_plot         # Cola para enviar datos al plotter
        self.bin_msm_format = ">10Hc2c"        # Formato del mensaje binario
        self.baudrate = 115200               # Velocidad de transmisión
        # El tamaño del mensaje es el tamaño del struct más la longitud de la marca de fin
        self.msm_size = struct.calcsize(self.bin_msm_format) + len(";****".encode())
        # Se listan los puertos disponibles
        self.ports = [port.device for port in list_ports.comports()]
        self.running = False                 # Bandera de ejecución
        self.buffer_publish = {}             # Buffer para publicar datos
        self.save_active = False             # Flag para activar el guardado
        self.plot_active = False             # Flag para activar el plotado
        self.serial_connections = []         # Lista de conexiones seriales
        self.buffers = []                    # Buffer para cada conexión

    def set_save_active(self, active):
        self.save_active = active
        print(f"Guardado activo: {active}")

    def set_plot_active(self, active):
        self.plot_active = active
        print(f"Plotado activo: {active}")

    def decode_serial_message(self, message):
        # Decodifica el mensaje recibido según el formato
        value = struct.unpack(self.bin_msm_format, message)
        return list(value[:10]), int(value[12])

    def open_serial_ports(self):
        ports = self.ports
        self.ports = []
        self.serial_connections = []
        for port in ports:
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
        for comm in self.serial_connections:
            comm.close()
            print(f"Puerto {comm.port} cerrado exitosamente.")

    def read_port_data(self, i):
        comm = self.serial_connections[i]
        data = comm.read(comm.in_waiting or self.msm_size)
        self.buffers[i].extend(data)
        end = self.buffers[i].find(b";****")
        values, body = None, None
        if end >= 0:
            message = self.buffers[i][:end]
            self.buffers[i] = self.buffers[i][end + len(b";****"):]
            if len(message) == self.msm_size - len(b";****"):
                return self.decode_serial_message(message)
        return values, body

    def identify_comm_mfl(self):
        """
        Identifica qué puerto corresponde a cada “cuerpo” (dispositivo).
        Se asume que se deben identificar tres cuerpos.
        """
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
        # Ordenar los puertos según el número de cuerpo identificado
        self.ports = [port_to_body[i] for i in sorted(port_to_body.keys())]
        print(f"Los puertos identificados en orden son {self.ports}")
        # Reabrir los puertos identificados
        self.open_serial_ports()

    def publish_data(self):
        n_ports = len(self.ports)
        # Diccionario para almacenar datos adquiridos temporalmente
        buffer_acquisition = {i: [] for i in range(n_ports)}
        iterations = 0
        print_iteration = 0
        self.buffer_publish = {i: [] for i in range(n_ports)}
        while self.running:
            start_time_bucle = time.time()
            # Leer datos de cada puerto
            for i in range(n_ports):
                values, body = self.read_port_data(i)
                if body is not None:
                    buffer_acquisition[body].append(values)

            # Si se han acumulado suficientes datos y está activado el plot, se envía a la cola de plot
            min_len = min(len(lst) for lst in buffer_acquisition.values()) if buffer_acquisition else 0
            if min_len % 10 == 0 and min_len >= 20 and self.plot_active:
                # Se envía una copia del buffer a la cola
                self.queue_plot.put(buffer_acquisition.copy())
                
            iterations += 1
            if min_len >= 300:
                print("elapsed time : %.4f, Iterations %s =================" % (
                    (time.time() - start_time_bucle), iterations - print_iteration))
                print_iteration = iterations
                for j, data in buffer_acquisition.items():
                    self.buffer_publish[j] = data[:300]
                    buffer_acquisition[j] = data[300:]
                    print(f"Para el cuerpo {j} el tamaño es {len(data)}")
                if self.save_active:
                    self.queue_save.put(self.buffer_publish.copy())

    def run(self):
        self.running = True
        # Activar guardado y plotado según la bandera global
        if save:
            self.set_save_active(True)
        if plot:
            self.set_plot_active(True)
        # Identificar puertos y luego iniciar la adquisición de datos
        self.identify_comm_mfl()
        try:
            self.publish_data()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        self.running = False
        self.close_serial_ports()


#%% Clase para Guardar Datos en CSV usando multiprocessing
class DataSaver:
    def __init__(self, queue_save):
        self.queue_save = queue_save      # Cola de datos a guardar
        self.running = True
        self.csv_file = None
        self.writer = None
        self.header_written = False

    def create_csv_file(self, num_bodies):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"datos_{timestamp}.csv"
        self.csv_file = open(filename, 'w', newline='')
        self.writer = csv.writer(self.csv_file)
        # Crear encabezado
        headers = []
        for body in range(num_bodies):
            for sensor in range(10):
                headers.append(f"b{body+1}_s{sensor}")
        self.writer.writerow(headers)
        self.header_written = True
        print(f"Archivo CSV {filename} creado.")

    def run(self):
        while self.running:
            try:
                # Espera hasta 0.5 s por nuevos datos
                data = self.queue_save.get(timeout=0.5)
                if not self.header_written:
                    num_bodies = len(data)
                    self.create_csv_file(num_bodies)
                # Convertir los datos a un array de NumPy y concatenarlos
                bodies = sorted(data.keys())
                array_list = []
                for body in bodies:
                    body_data = np.array(data[body], dtype=np.uint16)
                    array_list.append(body_data)
                data_array = np.concatenate(array_list, axis=1)
                csv_rows = data_array.tolist()
                # Escribir los datos en el archivo CSV
                self.writer.writerows(csv_rows)
                self.csv_file.flush()
            except Exception:
                # Puede ocurrir queue.Empty o cualquier otro error
                continue


#%% Clase para Plotear Datos en tiempo real usando multiprocessing
class DataPlot:
    def __init__(self, queue_plot):
        self.queue_plot = queue_plot      # Cola de datos para plotear
        self.running = True
        self.data = None

    def run(self):
        # Se crea una figura para el plot
        fig, ax = plt.subplots()
        
        def update(frame):
            # Se extraen todos los datos disponibles en la cola sin bloquear
            while not self.queue_plot.empty():
                try:
                    data = self.queue_plot.get_nowait()
                    try:
                        # Se arma un array a partir de los datos de cada cuerpo
                        data_array = np.column_stack([np.array(data[key])[-10:] for key in sorted(data.keys())])
                    except Exception as e:
                        print(f"Error concatenando datos: {e}")
                        continue
                    if self.data is None:
                        self.data = data_array
                    else:
                        self.data = np.vstack((self.data, data_array))
                        # Limitar el número de filas para evitar crecer sin límite
                        if self.data.shape[0] > 300:
                            self.data = self.data[-300:]
                except Exception as e:
                    print(e)
                    break
            # Actualizar el plot
            ax.clear()
            if self.data is not None and self.data.shape[0] > 0:
                x = np.arange(self.data.shape[0])
                num_lines = self.data.shape[1]
                for i in range(num_lines):
                    ax.plot(x, self.data[:, i], label=f"Body {i+1}")
                ax.legend()
            ax.set_xlim(0, 300)
            ax.set_ylim(0, 1024)  # Rango de sensor (ajustable)
            return []
        
        ani = FuncAnimation(fig, update, interval=100, blit=False)
        plt.show()


#%% Funciones “main” para cada proceso
def acquisition_process_main(queue_save, queue_plot):
    adq = DataAdquisition(queue_save, queue_plot)
    adq.run()

def saver_process_main(queue_save):
    saver = DataSaver(queue_save)
    try:
        saver.run()
    except KeyboardInterrupt:
        pass

def plot_process_main(queue_plot):
    plotter = DataPlot(queue_plot)
    try:
        plotter.run()
    except KeyboardInterrupt:
        pass


#%% Función principal: se crean y se inician los procesos
if __name__ == "__main__":
    # Se crean las colas de comunicación entre procesos
    queue_save = Queue()
    queue_plot = Queue()
    
    # Se crean los procesos para adquisición, guardado y plotado
    acq_process = Process(target=acquisition_process_main, args=(queue_save, queue_plot))
    saver_process = Process(target=saver_process_main, args=(queue_save,))
    plot_process = Process(target=plot_process_main, args=(queue_plot,))
    
    # Iniciar los procesos
    acq_process.start()
    saver_process.start()
    plot_process.start()
    
    try:
        # Bucle principal inactivo; los procesos trabajan de forma independiente
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Terminando procesos...")
        acq_process.terminate()
        saver_process.terminate()
        plot_process.terminate()
    
    acq_process.join()
    saver_process.join()
    plot_process.join()
