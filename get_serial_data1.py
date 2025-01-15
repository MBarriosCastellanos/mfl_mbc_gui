import serial
import struct
import csv
from datetime import datetime
import numpy as np
from serial.tools import list_ports

# Formato del mensaje binario
BIN_MSG_FORMAT = ">10Hc2c"

# Función para decodificar un mensaje serial
def decode_serial_message(message: bytearray) -> dict:
    value = struct.unpack(BIN_MSG_FORMAT, message)
    return {
        "values": list(value[0:10]),  # Valores de los sensores
        "status": int(value[12])      # Identificador del cuerpo
    }

# Configuración de puertos seriales
BAUDRATE = 115200

# Tamaño esperado del mensaje
MESSAGE_SIZE = struct.calcsize(BIN_MSG_FORMAT) + len(";****".encode())

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
    max_attempts = 10  # Máximo número de intentos por puerto

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

# Archivo CSV para guardar los datos
current_date = datetime.now().strftime("%Y-%m-%d")
csv_filename = f"datos_{current_date}.csv"
csv_file = open(csv_filename, mode='w', newline='')
csv_writer = csv.writer(csv_file)
header = [f"S{i:02d}_C{j}" for j in range(1, 4) for i in range(1, 11)] + ["ID_C1", "ID_C2", "ID_C3"]
csv_writer.writerow(header)

# Paso 1: Identificar qué puerto corresponde a cada cuerpo
ports = identify_com_connections()

serial_connections, buffers = get_serial_coneccions_buffers(ports)


# Crear buffers provisionales para cada cuerpo
buffer_provisional = {1: [], 2: [], 3: []}

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
                buffer_provisional[body_id1 + 1].append(decoded_message1["values"])
        if end_marker2>=0:
            message2 = buffers[ports[1]][:end_marker2]
            buffers[ports[1]] = buffers[ports[1]][end_marker2 + len(b";****"):]
            if len(message2) == MESSAGE_SIZE - len(b";****"):
                decoded_message2 = decode_serial_message(message2)
                body_id2 = decoded_message2["status"]
                buffer_provisional[body_id2 + 1].append(decoded_message2["values"])
        if end_marker3>=0:
            message3 = buffers[ports[2]][:end_marker3]
            buffers[ports[2]] = buffers[ports[2]][end_marker3 + len(b";****"):]
            if len(message3) == MESSAGE_SIZE - len(b";****"):
                decoded_message3 = decode_serial_message(message3)
                body_id3 = decoded_message3["status"]
                buffer_provisional[body_id3 + 1].append(decoded_message3["values"])

        print(len(buffer_provisional[1]), len(buffer_provisional[2]), len(buffer_provisional[3]))
        

        #for port, comm in zip(ports, serial_connections):
        #    # Leer datos del puerto actual
        #    data = comm.read(comm.in_waiting or 1)
        #    buffers[port].extend(data)
#
        #    # Buscar el fin de línea en el buffer
        #    end_marker = buffers[port].find(b";****")
        #    if end_marker >= 0:
        #        # Extraer un mensaje completo del buffer
        #        message = buffers[port][:end_marker]
        #        buffers[port] = buffers[port][end_marker + len(b";****"):]
#
        #        # Verificar el tamaño del mensaje
        #        if len(message) == MESSAGE_SIZE - len(b";****"):
        #            decoded_message = decode_serial_message(message)
        #            body_id = decoded_message["status"]
        #            buffer_provisional[body_id + 1].append(decoded_message["values"])
#
        #        # Transferir al buffer maestro si los tres cuerpos tienen datos
        #        if all(len(buffer_provisional[body]) >= 100 for body in buffer_provisional):
        #            # Concatenar datos en el buffer maestro en orden
        #            print("Datos completos para los cuerpos 1, 2 y 3.")
        #            print(np.array(buffer_provisional[1]).shape)
        #            print(np.array(buffer_provisional[2]).shape)
        #            print(np.array(buffer_provisional[3]).shape)
#
        #            buffer_master = []
        #            for body_id in range(1, 4):  # Orden 1, 2, 3
        #                buffer_master.extend(buffer_provisional[body_id])
        #                buffer_provisional[body_id] = []  # Vaciar el buffer provisional
#
        #            # Escribir datos al archivo CSV
        #            for row in buffer_master:
        #                csv_writer.writerow(row)
#
except KeyboardInterrupt:
    pass  # Permitir salir del bucle con Ctrl+C
#
## Cerrar puertos y archivo
#for comm in serial_connections:
#    comm.close()
#csv_file.close()
#print("Todos los puertos cerrados y datos guardados correctamente.")
#