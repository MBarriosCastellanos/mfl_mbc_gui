# =============================================================================
# Graficas, Librerias y definiciones
# =============================================================================
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
colors = [(0,    (1, 1, 1)),       # Green
          (1,    (1,     0, 0))]      # red
cmap1 = LinearSegmentedColormap.from_list('custom_cmap', colors, N=2)
labels = [f's{i+1}' for i in range(10)]

# =============================================================================
# Scan A
# =============================================================================
def ScanA_create(y_min, y_max, t_max):
  # Setup plot area with subplots
  fig, ax = plt.subplots(3, 1, figsize=(6, 4), dpi=150, sharex=True)
  fig.subplots_adjust(left=0.12, right=0.86, top=0.93, bottom=0.1, hspace=0.07)  
  ax[2].set_xlabel("tiempo [s]")
  for i in range(3):
    ax[2-i].set_ylabel(f"Cuerpo {i+1}")
    ax[2-i].set_ylim([y_min, y_max])
  ax[0].set_xlim([0, t_max])
  ax[0].legend(labels, loc='upper right', bbox_to_anchor=(1.19, 0.5), ncol=1)
  return fig, ax

def ScanA_update(ax, y_min, y_max, t_max, data, sampling_rate, auto_scale):
  len_data = len(data)
  t = np.linspace(0, len_data-1, num=len_data)/sampling_rate
  for i in range(3):
    while ax[2-i].lines:
      ax[2-i].lines[0].remove()
    ax[2-i].plot(t, data[:, i*10: (i+1)*10])
    ax[2-i].set_xlim([0, t_max])
    if auto_scale==1:
      ax[2-i].set_ylim([data.min(), data.max()])
    else:
      ax[2-i].set_ylim([y_min, y_max])
  ax[0].legend(labels, loc='upper right', bbox_to_anchor=(1.19, 0.5),  ncol=1)
  return ax

# =============================================================================
# Alarma
# =============================================================================
def Alarm_create():
  # Configuración de la figura y ejes
  fig, ax = plt.subplots(3, 1, figsize=(1, 4), dpi=150, sharex=True)
  fig.subplots_adjust(left=0.3, right=0.9, top=0.93, 
                            bottom=0.1, hspace=0.007)

  # Preparación de datos para pcolormesh (necesitan ser 2D)
  # Bordes en X (debe tener 1 elemento más que la dimensión de los datos)
  x_edges = np.array([0.8, 1.2])  
  y_edges = np.linspace(0.3, 10.8, 11)  # 11 bordes para 10 celdas verticales

  X_alarm, Y_alarm = np.meshgrid(x_edges, y_edges)  # Crear mallas para pcolormesh
  Z_alarm = np.array([[0],[0],[0],[0],[0],[0],[0],[0],[0],[0]])

  for i in range(3):
    # Crear el gráfico de mapa de colores
    ax[i].pcolormesh(X_alarm, Y_alarm, Z_alarm, shading='flat', cmap=cmap1)
    
    # Configuración de ejes (similar al original)
    ax[i].set_ylabel(f"Cuerpo {i+1}")
    ax[i].set_ylim([0.3, 10.8])
    ax[i].set_yticks(np.linspace(1, 10, 10))  # Centros de las celdas
    ax[i].set_yticklabels(labels, fontsize=8)
    ax[i].set_xlim([0.8, 1.2])
    ax[i].set_xticks([1])  # Centros de las celdas
    ax[i].set_xticklabels([])  # Centros de las celdas
    ax[i].set_xlabel("Alarmas")  # Centros de las celdas
  return fig, ax, X_alarm, Y_alarm

def Alarm_update(ax, X_alarm, Y_alarm, data):
  # Actualizar los 3 subplots de alarmas
  for i in range(3):
    # Limpiar solo el contenido del gráfico, no la configuración
    for coll in ax[2-i].collections:
      coll.remove()
    # Crear nuevo gráfico con datos aleatorios
    ax[2-i].pcolormesh(X_alarm, Y_alarm, data[i],  shading='flat',cmap=cmap1)
  return ax