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

#%% Definir constantes
start_time = time.time()
BIN_MSG_FORMAT = ">10Hc2c"      # Formato de los datos en binario
BAUDRATE = 115200               # Velocidad de transmisión 
MESSAGE_SIZE = struct.calcsize( # Tamaño de los mensajes seriales
    BIN_MSG_FORMAT) + len(";****".encode())
save = True                     # Guardar datos en un archivo CSV
plot = True                     # Mostrar gráficos en tiempo real

#%% Definir funciones
def close_applications_using_port(port):
    """Cierra cualquier aplicación que esté utilizando el puerto serial."""
    try:
        if os.name == 'nt':  # Para Windows
            # Usa `handle.exe` para encontrar y cerrar aplicaciones
            result = subprocess.check_output(["handle.exe", port], universal_newlines=True)
            lines = result.split("\n")
            for line in lines:
                if "pid:" in line.lower():
                    pid = line.split("pid:")[1].split()[0]
                    subprocess.call(["taskkill", "/F", "/PID", pid])
        else:  # Para Linux/macOS
            # Usa `lsof` para encontrar y cerrar aplicaciones
            result = subprocess.check_output(["lsof", "|", "grep", port], universal_newlines=True, shell=True)
            lines = result.split("\n")
            for line in lines:
                pid = line.split()[1]
                subprocess.call(["kill", "-9", pid])
        print(f"Se cerraron las aplicaciones que utilizaban el puerto {port}.")
    except Exception as e:
        print(f"No se pudo cerrar las aplicaciones del puerto {port}: {e}")

def decode_serial_message(message: bytearray) -> dict:
    value = struct.unpack(BIN_MSG_FORMAT, message)
    return {
        "values": list(value[0:10]),  # Valores de los sensores
        "status": int(value[12])      # Identificador del cuerpo
    }
# functions
def get_serial_coneccions_buffers(ports): # Crear conexiones seriales
    serial_connections = []
    buffers = {}
    for port in ports:
        try:
            comm = serial.Serial(
                port=port,
                baudrate=BAUDRATE,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0.1
            )
            serial_connections.append(comm)
            buffers[port] = bytearray()
            print(f"Puerto {port} abierto exitosamente.")
        except Exception as e:
            print(f"Error al abrir el puerto {port}: {e}")
    return serial_connections, buffers

def identify_com_connections():
    ports = list_ports.comports()
    ports = [port.device for port in ports]
    #ports = ["COM3", "COM10", "COM12"]

    # Paso 0: Crear conexiones seriales
    serial_connections, buffers = get_serial_coneccions_buffers(ports)
    ports = list(buffers.keys())

    # Paso 1: Identificar qué puerto corresponde a cada cuerpo
    port_to_body = {}
    max_attempts = 50  # Máximo número de intentos por puerto

    # Mientras no se hayan identificado los 3 cuerpos
    while len(port_to_body) < 3:
        for port, comm in zip(ports, serial_connections):
            # Si el puerto ya ha sido asignado, pasar al siguiente
            if port in port_to_body.values():
                continue

            print(f"Intentando identificar cuerpo para el puerto {port}...")
            attempts = 0
            while attempts < max_attempts:
                try:
                    # Leer datos del puerto
                    data = comm.read(comm.in_waiting or MESSAGE_SIZE)
                    buffers[port].extend(data)

                    # Buscar el fin de línea en el buffer
                    end_marker = buffers[port].find(b";****")
                    if end_marker >= 0:
                        # Extraer un mensaje completo del buffer
                        message = buffers[port][:end_marker]
                        buffers[port] = buffers[port][end_marker + len(b";****"):]

                        # Verificar el tamaño del mensaje
                        if len(message) == MESSAGE_SIZE - len(b";****"):
                            decoded_message = decode_serial_message(message)
                            body_id = decoded_message["status"]

                            # Asignar puerto al cuerpo y salir del bucle
                            port_to_body[body_id] = port
                            print(f"El puerto {port} corresponde al cuerpo {body_id + 1}.")
                            comm.close()
                            break
                except Exception as e:
                    print(f"Error durante la identificación del puerto {port}: {e}")
               
                attempts += 1

            # Si no se pudo identificar el cuerpo, continuar con el siguiente puerto
            if attempts == max_attempts and port not in port_to_body.values():
                print(f"No se pudo identificar un cuerpo para el puerto {port} después de {max_attempts} intentos.")

        # Salir del bucle principal si todos los cuerpos han sido identificados
        if len(port_to_body) == 3:
            print("Todos los cuerpos han sido identificados correctamente.")
            break
        
    # Verificar que se han identificado
    ports = [port_to_body[i] for i in sorted(port_to_body.keys())]
    print("Puertos identificados:", ports)
    return ports

#%% Archivo CSV para guardar los datos
current_date = datetime.now().strftime("%Y-%m-%d")
csv_filename = f"datos_{current_date}.csv"


#%% Paso 1: Identificar qué puerto corresponde a cada cuerpo
ports = identify_com_connections()

#%% Paso 2: Leer datos de los puertos seriales
serial_connections, buffers = get_serial_coneccions_buffers(ports)

# Crear buffers 
buffer_acquisition = {1: [], 2: [], 3: []}
buffer_plot = {1: np.empty((0, 10)), 2: np.empty((0, 10)), 3: np.empty((0, 10))}
iterations = 0
plot_refresh = 100
plot_samples = 1500
header = [f"S{i:02d}_C{j}" for j in range(1, 4) for i in range(1, 11)] # Encabezado del archivo CSV
if plot:
    fig, axs = plt.subplots(3, 1, figsize=(10, 10))
    for i, ax in enumerate(axs):
        ax.set_ylabel(f"Cuerpo {i + 1}")
        ax.set_xlabel("time")
        ax.set_ylim(0, 10)
        ax.grid()

try:
    while True:
        comm1 = serial_connections[0]
        comm2 = serial_connections[1]
        comm3 = serial_connections[2]
        data1 = comm1.read(comm1.in_waiting or 1)
        data2 = comm2.read(comm2.in_waiting or 1)
        data3 = comm3.read(comm3.in_waiting or 1)
        buffers[ports[0]].extend(data1)
        buffers[ports[1]].extend(data2)
        buffers[ports[2]].extend(data3)

        # Buscar el fin de línea en el buffer
        end_marker1 = buffers[ports[0]].find(b";****")
        end_marker2 = buffers[ports[1]].find(b";****")
        end_marker3 = buffers[ports[2]].find(b";****")

        if end_marker1>=0:
            message1 = buffers[ports[0]][:end_marker1]
            buffers[ports[0]] = buffers[ports[0]][end_marker1 + len(b";****"):]
            if len(message1) == MESSAGE_SIZE - len(b";****"):
                decoded_message1 = decode_serial_message(message1)
                body_id1 = decoded_message1["status"]
                buffer_acquisition[body_id1 + 1].append(decoded_message1["values"])
        if end_marker2>=0:
            message2 = buffers[ports[1]][:end_marker2]
            buffers[ports[1]] = buffers[ports[1]][end_marker2 + len(b";****"):]
            if len(message2) == MESSAGE_SIZE - len(b";****"):
                decoded_message2 = decode_serial_message(message2)
                body_id2 = decoded_message2["status"]
                buffer_acquisition[body_id2 + 1].append(decoded_message2["values"])
        if end_marker3>=0:
            message3 = buffers[ports[2]][:end_marker3]
            buffers[ports[2]] = buffers[ports[2]][end_marker3 + len(b";****"):]
            if len(message3) == MESSAGE_SIZE - len(b";****"):
                decoded_message3 = decode_serial_message(message3)
                body_id3 = decoded_message3["status"]
                buffer_acquisition[body_id3 + 1].append(decoded_message3["values"])
        iterations += 1


        if plot and iterations % plot_refresh == 0 and iterations > 1200:
            buffer_plot[1] = np.vstack((buffer_plot[1], np.array(buffer_acquisition[1][-plot_refresh:])))
            buffer_plot[2] = np.vstack((buffer_plot[2], np.array(buffer_acquisition[2][-plot_refresh:])))
            buffer_plot[3] = np.vstack((buffer_plot[3], np.array(buffer_acquisition[3][-plot_refresh:])))

            for i, ax in enumerate(axs):
                ax.clear()
                t = np.arange(buffer_plot[i + 1].shape[0])/300
                ax.plot(buffer_plot[i + 1])
                ax.set_ylabel(f"Cuerpo {i + 1}")
                ax.set_xlabel("time")
                #ax.set_ylim(0, 10)
                ax.grid()
            plt.pause(0.01)
            if len(buffer_plot[1]) > (plot_samples - plot_refresh):
                buffer_plot[1] = buffer_plot[1][-(plot_samples - plot_refresh):]
                buffer_plot[2] = buffer_plot[2][-(plot_samples - plot_refresh):]
                buffer_plot[3] = buffer_plot[3][-(plot_samples - plot_refresh):]

        if len(buffer_acquisition[1]) >=300 and len(buffer_acquisition[2]) >=300 and len(buffer_acquisition[3]) >=300:
            if save:
                buffer_body1 = np.array(buffer_acquisition[1])
                buffer_body2 = np.array(buffer_acquisition[2])
                buffer_body3 = np.array(buffer_acquisition[3])
                buffer_save = np.c_[buffer_body1[:300, :], buffer_body2[:300, :], buffer_body3[:300, :],]
                with open(csv_filename, mode='a', newline='') as csv_file:
                    if csv_file.tell() == 0:
                        csv_writer = csv.writer(csv_file)
                        csv_writer.writerow(header)
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerows(buffer_save)
                del buffer_save, buffer_body1, buffer_body2, buffer_body3
                print("Datos guardados en el archivo CSV.")
                print("elapsed time : %.4f" % (time.time() - start_time))
                print("len 1 : {}, len 2 : {}, len 3 : {}".format(len(buffer_acquisition[1]), len(buffer_acquisition[2]), len(buffer_acquisition[3])))
            buffer_acquisition = {1: [], 2: [], 3: []}

except KeyboardInterrupt:
    pass  # Permitir salir del bucle con Ctrl+C
