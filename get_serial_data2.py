import serial
import struct
import csv
from datetime import datetime

# Definir el formato del mensaje binario
BIN_MSG_FORMAT = ">10Hc2c"  # 10 valores enteros sin signo, 1 carácter y 2 caracteres adicionales

# Función para decodificar un mensaje serial
# Desempaqueta el mensaje según el formato definido y lo convierte en un diccionario
def decode_serial_message(message: bytearray) -> dict:
    if len(message) != struct.calcsize(BIN_MSG_FORMAT):
        raise ValueError("El tamaño del mensaje no coincide con el formato esperado")
    value = struct.unpack(BIN_MSG_FORMAT, message)
    return {
        "values": list(value[0:10]),  # Extrae los primeros 10 valores como lista
        "status": int(value[12])  # Obtiene el estado como un entero
    }

# Configuración de los puertos seriales
BAUDRATE = 115200  # Velocidad de comunicación en baudios
PORTS = ["COM10", "COM11", "COM3"]  # Lista de puertos COM específicos

# Tamaño esperado de los mensajes según el formato definido
MESSAGE_SIZE = struct.calcsize(BIN_MSG_FORMAT) + len(";****".encode())

# Generar nombre de archivo con la fecha actual
current_date = datetime.now().strftime("%Y-%m-%d")
csv_filename = f"datos_{current_date}.csv"

# Abrir archivo CSV para guardar los datos
csv_file = open(csv_filename, mode='w', newline='')
csv_writer = csv.writer(csv_file)

# Escribir encabezados en el archivo CSV
header = [f"S{i:02d}" for i in range(1, 11)] + ["cuerpo"]
csv_writer.writerow(header * 3)  # Tres grupos de 11 columnas

# Intentar abrir todos los puertos seriales
serial_connections = []
for port in PORTS:
    try:
        comm = serial.Serial(
            port=port,
            baudrate=BAUDRATE,  # Velocidad de transmisión
            parity=serial.PARITY_NONE,  # Sin paridad
            stopbits=serial.STOPBITS_ONE,  # Un bit de parada
            bytesize=serial.EIGHTBITS,  # Tamaño del byte: 8 bits
            timeout=None  # Sin timeout para garantizar lectura continua
        )
        serial_connections.append(comm)
        print(f"Puerto {port} abierto exitosamente.")
    except Exception as e:
        print(f"Error al abrir el puerto {port}: {e}")

# Buffer para almacenar datos incompletos de cada puerto
buffers = [bytearray() for _ in serial_connections]

try:
    while True:
        row_data = []
        for i, comm in enumerate(serial_connections):
            # Leer un mensaje completo del puerto actual
            while len(buffers[i]) < MESSAGE_SIZE:
                data = comm.read(MESSAGE_SIZE - len(buffers[i]))  # Leer solo los bytes necesarios
                buffers[i].extend(data)  # Añadir los datos leídos al buffer correspondiente

            # Verificar si el buffer tiene suficiente tamaño para un mensaje completo
            if len(buffers[i]) >= MESSAGE_SIZE:
                # Extraer un mensaje completo del buffer
                message = buffers[i][:MESSAGE_SIZE]
                buffers[i] = buffers[i][MESSAGE_SIZE:]  # Eliminar el mensaje del buffer

                try:
                    # Decodificar el mensaje y agregarlo a la fila actual
                    decoded_message = decode_serial_message(message)
                    row_data.extend(decoded_message["values"] + [decoded_message["status"]])
                except ValueError as e:
                    print(f"Error de decodificación: {e}")
                    row_data.extend([None] * 11)  # Rellenar con valores nulos en caso de error
            else:
                row_data.extend([None] * 11)  # Rellenar si no hay datos suficientes

        # Escribir la fila en el archivo CSV
        if row_data:
            csv_writer.writerow(row_data)

except KeyboardInterrupt:
    pass  # Permite salir del bucle con Ctrl+C

# Cerrar los puertos seriales y el archivo CSV
for comm in serial_connections:
    comm.close()
csv_file.close()
print("Todos los puertos cerrados y datos guardados correctamente.")
