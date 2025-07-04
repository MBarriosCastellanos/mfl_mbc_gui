#%% ===========================================================================
# Graficas, Librerias y definiciones
# =============================================================================
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import BoundaryNorm
import numpy as np

import matplotlib as mpl

# Configurar parámetros globales
mpl.rcParams.update({
    # Colores de fondo
    'figure.facecolor': 'black',
    'axes.facecolor': 'black',
    
    # Color del borde del marco (axes edge)
    'axes.edgecolor': '#bac2ba',
    
    # Ciclo de colores para las líneas (10 primeros)
    'axes.prop_cycle': mpl.cycler(color=[
      '#FF9933',  # Naranja (0°-30°)
      '#FFD700',  # Oro (50°)
      '#FFFF33',  # Amarillo (60°)
      '#CCFF00',  # Lima (75°)
      '#ADFF2F',  # Verde-amarillo (85°)
      '#39FF14',  # Verde (120°)
      '#00FFFF',  # Cian (180°)
      '#00CCFF',  # Azul claro (195°)
      '#FF66FF',  # Rosa (300°)
      '#FF33CC',  # Magenta (320°)
    ]),
    
    # Estilo de texto y ejes
    'text.color': 'white',           # Color del texto
    'axes.labelcolor': 'white',    # Color de etiquetas de ejes
    'xtick.color': 'white',        # Color de marcas eje X
    'ytick.color': 'white'         # Color de marcas eje Y
})

colors1 = [(0, (0, 0, 0)),    
           (0.5, (0, 0.5, 0)),
          (1, (0, 1, 0))]     
cmap1 = LinearSegmentedColormap.from_list('custom_cmap', colors1, N=2)
labels = [f's{i+1}' for i in range(10)]
label= 'Campo Magnético [kA/m]'

colors2 = [(0, (0, 1, 0)),      # Green
          (0.25, (0.8, 1, 0)),       # Light green
          (0.5, (1, 1, 0)),    # yellow
          (0.75, (1, 0.5, 0)),       # orange
          (1, (1, 0, 0))]      # red
cmap2 = LinearSegmentedColormap.from_list('custom_cmap', colors2, 
                                          N=7
                                          )

#%% ===========================================================================
# Scan A
# =============================================================================
def ScanA_create(y_min, y_max, t_max):
  """
  Crea la figura y los ejes para la visualización de Scan A.
  y_min: Valor mínimo en el eje y
  y_max: Valor máximo en el eje y
  t_max: Valor máximo en el eje x (tiempo)
  """
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
  """
  Actualiza la figura y los ejes para la visualización de Scan A.
  fig: Figura creada previamente
  ax: Ejes creados previamente
  y_min: Valor mínimo en el eje y
  y_max: Valor máximo en el eje y  
  t_max: Valor máximo en el eje x (tiempo)
  data: Datos a visualizar
  sampling_rate: Frecuencia de muestreo
  auto_scale: Si es 1, se ajusta automáticamente el rango en y
  """
  len_data = len(data)
  t = np.linspace(0, len_data-1, num=len_data)/sampling_rate

  y_min, y_max = sorted([y_min, y_max])

  for i in range(3):
    while ax[2-i].lines:
      ax[2-i].lines[0].remove()
    data_plot = data[:, i*10: (i+1)*10] # Seleccionar datos de un cuerpo
    ax[2-i].plot(t, data_plot[:, ::-1]) # invertir señales para ajustar al label
    ax[2-i].set_xlim([0, t.max()])
    if auto_scale==1:
      ax[2-i].set_ylim([data.min(), data.max()])
    else:
      ax[2-i].set_ylim([y_min, y_max])
  ax[0].legend(labels[::-1], loc='upper right', bbox_to_anchor=(1.19, 0.5),  ncol=1)
  return fig, ax

#%% ===========================================================================
# Scan C
# =============================================================================
def ScanC_create(z_min, z_max, t_max):
  """
  Crea la figura y los ejes para la visualización de Scan C.
  z_min: Valor mínimo en el eje z
  z_max: Valor máximo en el eje z
  t_max: Valor máximo en el eje x (tiempo)
  """
  n_y = 10     # Número de puntos en el eje y
  y = np.linspace(1, 10, n_y)
  fig, ax = plt.subplots(3, 1, figsize=(6, 4), dpi=150, sharex=True)
  fig.subplots_adjust(left=0.10, right=1, top=0.98, bottom=0.10, 
    hspace=0.04)
  ax[2].set_xlabel("tiempo [s]")
  
  for i in range(3):
    ax[2 - i].set_ylabel(f"Cuerpo {i + 1}")
    ax[2 - i].set_ylim([0.5, 10.5])
    ax[2 - i].set_yticks(y)
    ax[2 - i].set_yticklabels(labels)

  # Crear un ScalarMappable para la colorbar
  norm = plt.Normalize(z_min, z_max)
  fig.sm = plt.cm.ScalarMappable(cmap=cmap2, norm=norm)
  fig.sm.set_array([])
  
  # Crear la colorbar una única vez
  fig.cbar = fig.colorbar(fig.sm, ax=ax, pad=0.01, )
  fig.cbar.set_label(label)
  #fig.cbar.add_axes([0.87, 0.15, 0.03, 0.7])  # [left, bottom, width, height]

  ## Inicializar un colorbar básico (se actualizará posteriormente)
  #sm = plt.cm.ScalarMappable(cmap=cmap2)
  #sm.set_array([])  # Array vacío inicialmente
  ## Añadir colorbar a la figura
  #cbar_ax = fig.add_axes([0.87, 0.15, 0.03, 0.7])  # [left, bottom, width, height]
  #cbar = fig.colorbar(sm, cax=cbar_ax)
  #cbar.set_label(label)  # Usar la variable global label
  #
  ## Guarda el axis de la colorbar como propiedad de la figura para referencia futura
  #fig.cbar_ax = cbar_ax

  return fig, ax

def ScanC_update(fig, ax, z_min, z_max, t_max, data, sampling_rate, auto_scale):
  """
  Actualiza la figura y los ejes para la visualización de Scan C.
  fig: Figura creada previamente
  ax: Ejes creados previamente
  z_min: Valor mínimo en el eje z
  z_max: Valor máximo en el eje z
  t_max: Valor máximo en el eje x (tiempo)
  data: Datos a visualizar
  sampling_rate: Frecuencia de muestreo
  auto_scale: Si es 1, se ajusta automáticamente el rango en z
  """
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

  # Asegurar que haya al menos 2 valores distintos para evitar errores
  if vmin == vmax:
      vmax += 1e-6  # Pequeño incremento para evitar colapso

  num_colors = 7  # Debe coincidir con N=7 del cmap2
  boundaries = np.linspace(vmin, vmax, num=num_colors + 1)  # 8 límites para 7 colores
  norm = BoundaryNorm(boundaries=boundaries, ncolors=num_colors)  # ncolors=7

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
    cs = ax[2-i].contourf(X, Y, Z, cmap=cmap2, alpha=0.9, norm=norm)
    mappables.append(cs)  # Guardar referencia al último mappable

  ax[0].set_xlim([0, t.max()])

  # Actualizar colorbar existente (sin crear/eliminar)
  if hasattr(fig, 'sm'):
    fig.sm.set_norm(norm)  # Actualizar la normalizacion
    fig.cbar.update_normal(fig.sm)  # Actualizar la colorbar

  ## Limpiar colorbar anterior si existe
  #if hasattr(fig, 'cbar_ax'):
  #  fig.cbar_ax.clear()
  #
  #  # Crear nueva colorbar con los límites actualizados
  #  #cbar_ax = fig.add_axes([0.87, 0.15, 0.03, 0.7])  # [left, bottom, width, height]
  #  sm = plt.cm.ScalarMappable(cmap=cmap2, norm=norm)
  #  sm.set_array([])  # No se necesita un array real, solo los límites de norm
  #  cbar = fig.colorbar(sm, cax=fig.cbar_ax)
  #  cbar.set_label(label)  # Usar la variable global label
  
  return fig, ax

#%% ===========================================================================
# Plot Alarma
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
    ax[i].set_ylabel(f"Cuerpo {i+1}")         # Nombrar ejes
    ax[i].set_ylim([0.3, 10.8])               # Limites del eje y
    ax[i].set_yticks(np.linspace(1, 10, 10))  # Ticks en el eje y
    ax[i].set_yticklabels(labels, fontsize=8) # Etiquetas en el eje y
    ax[i].set_xlim([0.8, 1.2])                # Limites del eje x
    ax[i].set_xticks([1])                     # ticks en el eje x
    ax[i].set_xticklabels([])  # Etiquetas en el eje x
    ax[i].set_xlabel("Alarmas")  # Etiqueta en el eje x
  return fig, ax, X_alarm, Y_alarm  # Devolver fig, ax y mallas

def Alarm_update(ax, X_alarm, Y_alarm, data):
  """#Actualizar los 3 subplots de alarmas con nuevos datos"""
  for i in range(3): # Recorrer los 3 subplots
    # Limpiar solo el contenido del gráfico, no la configuración
    for coll in ax[2-i].collections: # Recorrer los objetos del gráfico
      coll.remove()                   # Eliminar el objeto
    # Crear nuevo gráfico con datos aleatorios
    ax[2-i].pcolormesh(X_alarm, Y_alarm, data[i],  shading='flat',cmap=cmap1)
  return ax       # Devolver ejes actualizados

#%% ===========================================================================
# Verification function
# =============================================================================
def verify_empty(variable, value): 
  """
  Verifica si se obtiene el valor, caso contrario devuelve un valor por defecto
  variable: variable a verificar
  value: valor por defecto
  """
  try: # Intentar obtener escala de los ejes
    return  variable.get()
  except: # Si falla, establecer valores por defecto
    return value
  