# =============================================================================
# Graficas, Librerias y definiciones
# =============================================================================
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import BoundaryNorm
import numpy as np
colors = [(0,    (1, 1, 1)),       # Green
          (1,    (1,     0, 0))]      # red
cmap1 = LinearSegmentedColormap.from_list('custom_cmap', colors, N=2)
labels = [f's{i+1}' for i in range(10)]
label= 'Campo Magnético [kA/m]'

colors2 = [(0,    (0,    0.5, 0)),      # Green
          (0.25, (0.35, 0.7, 0)),       # Light green
          (0.5,  (0.95,   0.95, 0)),    # yellow
          (0.75, (0.7, 0.35, 0)),       # orange
          (1,    (0.5,     0, 0))]      # red
cmap2 = LinearSegmentedColormap.from_list('custom_cmap', colors2, 
                                          N=7
                                          )
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

def ScanA_update(fig, ax, y_min, y_max, t_max, data, sampling_rate, auto_scale):
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
  return fig, ax

# =============================================================================
# Scan C
# =============================================================================
def ScanC_create(z_min, z_max, t_max):
  # Generar datos de tiempo y valores y
  #n_time = 1500  # Número de puntos en el tiempo
  n_y = 10     # Número de puntos en el eje y
  #t = np.linspace(0, t_max, n_time)
  y = np.linspace(1, 10, n_y)
  #X, Y = np.meshgrid(t, y)  # Crear mallas para las coordenadas
  
  # Niveles de contorno basados en z_min y z_max
  #contour_levels = np.linspace(z_min, z_max, num=15)
  #Z = np.ones((n_y, n_time))*z_min
  
  # Configurar gráficos
  fig, ax = plt.subplots(3, 1, figsize=(6, 4), dpi=150, sharex=True)
  fig.subplots_adjust(left=0.10, right=0.99, top=0.98, bottom=0.10, 
    hspace=0.04)
  ax[2].set_xlabel("tiempo [s]")
  
  for i in range(3):
    ax[2 - i].set_ylabel(f"Cuerpo {i + 1}")
    ax[2 - i].set_ylim([0.5, 10.5])
    ax[2 - i].set_yticks(y)
    ax[2 - i].set_yticklabels(labels)
  
  #ax[0].set_xlim([0, t_max])
  

  return fig, ax

def ScanC_update(fig, ax, z_min, z_max, t_max, data, sampling_rate, auto_scale):
  n_y = 10  # Filas fijas
  y = np.linspace(1, 10, n_y)
  M = int(t_max * sampling_rate)  # Columnas por cuerpo
  cuerpos = 3
  # Actualizar geometría temporal
  len_data = len(data)
  t = np.linspace(0, len_data-1, num=len_data)/sampling_rate
  X, Y = np.meshgrid(t, y)

  # Determinar límites globales
  if auto_scale:
    vmin, vmax = data.min(), data.max()
  else:
    vmin, vmax = sorted([z_min, z_max])

  # --- Corrección clave: Definir boundaries y norm correctamente ---
  num_colors = 7  # Debe coincidir con N=7 del cmap2
  boundaries = np.linspace(vmin, vmax, num=num_colors + 1)  # 8 límites para 7 colores
  norm = BoundaryNorm(boundaries=boundaries, ncolors=num_colors)  # ncolors=7

  # Determinar niveles dinámicos
  #cl = np.linspace(vmin, vmax, 7)

  # Ajustar datos si es necesario
  data = data[:, :cuerpos*M]  # Truncar a máximo de columnas esperadas

  # Lista para guardar los últimos mappables
  mappables = []

  for i in range(cuerpos): 
    Z = data[:, i*n_y:(i+1)*n_y].T
    
    # Limpiar contornos anteriores
    for coll in ax[2-i].collections:
      coll.remove()

    # Dibujar nuevos contornos
    cs = ax[2-i].contourf(X, Y, Z, cmap=cmap2, alpha=0.9, norm=norm,
      #levels=cl,
      #vmin=vmin, vmax=vmax
      )
    mappables.append(cs)  # Guardar referencia al último mappable

  ax[0].set_xlim([0, t.max()])
  b_labels = [int(i) for i in boundaries]

  #if hasattr(fig, 'cbar'):
    #fig.cbar.remove()  # Eliminar colorbar anterior
    #fig.cbar.update_normal(cs)  # Sincronizar con el nuevo mappable
    #fig.cbar.mappable.set_clim(vmin=vmin, vmax=vmax)
    #fig.cbar.mappable.set_norm(norm)
    #fig.cbar.set_ticks(boundaries) 
    #fig.cbar.set_ticklabels([f"{int(x)}" for x in boundaries])
    #fig.cbar.formatter("{x:.0ef}")
    #fig.cbar._draw_all()
  #else:
    #fig.cbar = fig.colorbar(cs, ax=ax, orientation='vertical', pad=0.05)
    #fig.cbar.mappable.set_clim(vmin=vmin, vmax=vmax)
    #fig.cbar.set_ticks(boundaries)
    #fig.cbar.set_ticklabels([f"{int(x)}" for x in boundaries])
    #fig.cbar.formatter("{x:.0ef}")
    #fig.cbar._draw_all()

  # Crear nueva colorbar usando el último mappable válido
  #fig.cbar = fig.colorbar(mappables[-1], ax=ax, orientation='vertical', pad=0.05)
  #fig.cbar.set_ticks(boundaries)
  #fig.cbar.set_ticklabels([f"{x:.0f}" for x in boundaries])
  
  # Forzar actualización de la figura
  #fig.canvas.draw()

  return fig, ax

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