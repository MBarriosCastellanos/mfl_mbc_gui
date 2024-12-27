import serial
import struct
import csv
from datetime import datetime

# Definir el formato del mensaje binario
BIN_MSG_FORMAT = ">10Hc2c"  # 10 valores enteros sin signo, 1 carácter y 2 caracteres adicionales

# Función para decodificar un mensaje serial
def decode_serial_message(message: bytearray) -> dict:
    if len(message) != struct.calcsize(BIN_MSG_FORMAT):
        raise ValueError("El tamaño del mensaje no coincide con el formato esperado")
    value = struct.unpack(BIN_MSG_FORMAT, message)
    return {
        "values": list(value[0:10]),  # Extrae los primeros 10 valores como lista
        "status": int(value[12])  # Obtiene el estado como un entero
    }

# Configuración de los puertos seriales
BAUDRATE = 115200
PORTS = ["COM10", "COM11", "COM3"]

# Tamaño esperado de los mensajes
MESSAGE_SIZE = struct.calcsize(BIN_MSG_FORMAT) + len(";****".encode())

# Generar nombre de archivo con la fecha actual
current_date = datetime.now().strftime("%Y-%m-%d")
csv_filename = f"datos_{current_date}.csv"

# Inicializar buffers de filas para cada puerto
buffers = [[] for _ in PORTS]
BUFFER_SIZE = 50  # Número de filas antes de escribir al archivo

# Abrir archivo CSV para guardar los datos
with open(csv_filename, mode='w', newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    header = [f"S{i:02d}" for i in range(1, 11)] + ["cuerpo"]
    csv_writer.writerow(header * len(PORTS))

    # Intentar abrir todos los puertos seriales
    serial_connections = []
    for port in PORTS:
        try:
            comm = serial.Serial(
                port=port,
                baudrate=BAUDRATE,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=None
            )
            serial_connections.append(comm)
            print(f"Puerto {port} abierto exitosamente.")
        except Exception as e:
            print(f"Error al abrir el puerto {port}: {e}")
            buffers.pop()  # Eliminar el buffer correspondiente si el puerto no puede abrirse

    try:
        while True:
            for i, comm in enumerate(serial_connections):
                # Leer datos del puerto
                buffer = bytearray()
                while len(buffer) < MESSAGE_SIZE:
                    data = comm.read(MESSAGE_SIZE - len(buffer))
                    buffer.extend(data)

                # Procesar el mensaje si está completo
                if len(buffer) == MESSAGE_SIZE:
                    try:
                        decoded_message = decode_serial_message(buffer)
                        row_data = decoded_message["values"] + [decoded_message["status"]]
                        buffers[i].append(row_data)  # Agregar al buffer del puerto

                        # Escribir al archivo si el buffer está lleno
                        if len(buffers[i]) >= BUFFER_SIZE:
                            csv_writer.writerows(buffers[i])  # Escribir las filas en el archivo
                            buffers[i].clear()  # Vaciar el buffer
                    except ValueError as e:
                        print(f"Error de decodificación en puerto {comm.port}: {e}")
                        buffers[i].append([None] * 11)  # Rellenar con valores nulos

    except KeyboardInterrupt:
        pass  # Permite salir del bucle con Ctrl+C

    # Escribir cualquier dato restante en los buffers
    for buffer in buffers:
        if buffer:
            csv_writer.writerows(buffer)

    # Cerrar puertos seriales
    for comm in serial_connections:
        comm.close()

print("Todos los puertos cerrados y datos guardados correctamente.")
