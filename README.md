# Componentes del equipo

  - Isabel del Rosario González Vega
  - David Arias Escribano
  - José Miguel Moreno García
  - Ana Martín Serrano

# Enlace al repositorio del proyecto:

  https://github.com/SSDD-2021-2022/SSDD-AM_JM_DA_IV

# Participación en el proyecto
  
  La puntuación obtenida se reparte equitativamente entre todos los miembros del equipo, 
  ya que todos los miembros han participado de igual manera.
  
# Archivos y carpetas

Este repositorio consiste en una plantilla de proyecto en Python. Contiene los
siguientes archivos y directorios:

- `IceFlix:` es el paquete principal de Python. En el se encuentran los principales 
  archivos .py que componen el proyecto
- `iceflix/__init__.py:` es un archivo vacío que necesita Python para
  reconozca el directorio `packagename` como un paquete/módulo de Python.
- `iceflix/cli.py:` contiene varias funciones que pueden manejar el
  puntos básicos de entrada a la consola definidos en `python.cfg`. El nombre de
  El submódulo y las funciones se pueden modificar si lo necesita.
- `iceflix.ice:` contiene la definición de interfaz de Slice para
  el proyecto.
- `iceflix/rtsputils.py:` contiene las clases para el emisor RTSP y
  jugador usando Gstreamer y VLC respectivamente.
- `pyproject.toml:` define el sistema de compilación utilizado en el proyecto.
- `run_client:` es un script que se puede ejecutar directamente desde el
  directorio raíz del repositorio. Sirve para ejecutar el IceFlix
  cliente.
- `run_iceflix:` es un script que se puede ejecutar directamente desde el
  directorio raíz del repositorio. Sirve para ejecutar todos los servicios
  en segundo plano para probar todo el sistema.
- `setup.cfg:` es un archivo de configuración de distribución de Python para
  herramientas de configuración. Necesita ser modificado para adecuarse a la
  nombre del paquete y funciones del controlador de la consola.
- `configs:` es una carpeta que contiene todos los archivos de configuración 
  necesarios para ejecutar el sistema.
- `data:` es una carpeta que contiene los datos persistentes del sistema,
  como el json de usuarios y la base de datos del catalogo.
- `resources:` es una carpeta que contiene un video de prueba ya subido con antelación
  para probar el sistema.
- `resources_to_upload:` es una carpeta que contiene una lista de videos listos para subirse
  mediante nuestra aplicacion.
- `CODEOWNERS:` contiene la informacion de los miembros del equipo.

# Ejecución del programa
  ## Iniciar el servidor de iceflix

  Para iniciarlo tenemos que escribir:
  
    ./run_iceflix 

  Si vemos que no se inicia y da un error de que no se puede ejecutar es porque *no* tiene permisos de ejecucion. Para solucionar este problema tenemos que ejecutar:
  
    chmod +x run_iceflix

  Ademas si sigue dando error hay que ejecutar primero el **icebox** con el siguiente comando:
  
    icebox --Ice.Config=./configs/icebox.config

  ## Iniciar el cliente
  
  Para inciar el cliente tenemos que poner el siguiente comando:
  
    ./run_client

  Al igual que antes, si vemos que no se inicia y da un error de que no se puede ejecutar es porque **no** tiene permisos de ejecucion. Para solucionar este problema tenemos que ejecutar:

    chmod +x run_client


  # Uso del programa
  
  Una vez iniciado el cliente primero hay que buscar el proxy del servidor (aparece en la pantalla de salida del terminal de iceflix) y hay que copiar lo siguiente (sin el 'Here you can see the MAIN proxy, enter it below:'):
 
    Here you can see the MAIN proxy, enter it below:
    796912BE-E4D0-418B-9EEB-EE454235EC16 -t -e 1.1:tcp -h 192.168.1.59 -p 40603 -t 60000:tcp -h 172.19.0.1 -p 40603 -t 60000:tcp -h 172.18.0.1 -p 40603 -t 60000:tcp -h 172.17.0.1 -p 40603 -t 60000:tcp -h 172.20.0.1 -p 40603 -t 60000

  El cual tenemos que copiar en la terminal del iceflix primero, y después en la del cliente, en concreta en la opcion 1 del menú inicial.

  Como deciamos antes nos vamos al cliente donde nos aparecen las sigueintes opciones:
  
  1.  Establecer conexión
  2.  Iniciar sesion
  3.  Buscar algo del catalogo
  4.  Salir de la aplicacion

  Las opciones 2 y 3 no se pueden ejecutar hasta que se haya establecido la conexion (opcion 1). Si no se incia sesion, se puede usar pero solo **se puede buscar por nombres y no por tags.**

  Sin embargo, si se incia sesion te dejará buscar por esas dos opciones.   

  Una vez que iniciemos la opcion 1 pegamos el proxy que habia en el terminal:
  en este caso de ejemplo hay que poner el proxy del caso anterior que se muestra:

    796912BE-E4D0-418B-9EEB-EE454235EC16 -t -e 1.1:tcp -h 192.168.1.59 -p 40603 -t 60000:tcp -h 172.19.0.1 -p 40603 -t 60000:tcp -h 172.18.0.1 -p 40603 -t 60000:tcp -h 172.17.0.1 -p 40603 -t 60000:tcp -h 172.20.0.1 -p 40603 -t 60000

  Una vez hecho iniciamos sesion si queremos tener mas opciones. Para hacerlo escribimos las credenciales de algún usuario añadido, por ejemplo este:
  
  - `Usuario` :  **ssdd**
  
  - `Contraseña` : **uclm**
  
  NOTA: se disponen de tres intentos para equivocarse al iniciar sesión, si se agotan, por seguridad el programa se cerrará.
  
  Y una vez inciado sesion el menú se ampliará con más opciones:

  1. Establecer conexión
  2. Iniciar sesion
  3. Salir de la sesion: por si se quiere cerrar la sesión con el usuario actual o iniciar sesión con un nuevo user.
  4. Opciones administrativas
  5. Ver el video por streaming
  6. Buscar por el catálogo
  7. Modificar informacion del catálogo
  8. Salir de la aplicación

  Como opciones nuevas podemos ver que estan del **3-5** y la **7-8**.
  A continuacion explicaremos como funcionan cada una:

  ### **Opciones adminstrativas:**

  Una vez puesto este menu aparecen 2 opciones:

  1. Añadir Usuario: introduciendo su nombre de usuario y su password correspondiente para añadirlo.
  2. Borrar Usuario: introduciendo el nombre de usuario del perfil que se desee eliminar.

  ### **Ver el video en streaming:**

  Para ver un video en streaming, primero debemos buscar en el catálogo dicho vídeo, bien por nombre o bien por tags, y a continuación simplemente tenemos que poner el id del video que se muestra en pantalla en los resultados de búsqueda. Una vez hecho, el video se reproduce durante 10 segundos y luego automaticamente se finaliza la conexión. Para probar esta funcionalidad, se puede reproducir el vídeo "slomo".

  ### **Buscar por el catálogo:**

  Existen dos modalidades de búsqueda de películas, por nombre y por tags. Si lo buscas por nombre se puede buscar mediante una palabra contenida en el nombre del video o con el nombre exacto. De la misma forma, con los tags funciona de manera similar, sin embargo en vez de poner el nombre del archivo se ponen las categorias o tags (etiquetas) que se hayan asignado previamente al video, separadas por ; cuando queremos introducir varias de ellas.
  NOTA: en la búsqueda por nombre, no se debe añadir el .mp4 al final del nombre del vídeo.

  ### **Modificar la informacion del catalogo:**

  1. Subir una pelicula: al pulsar esta opción se muestra el listado de películas que hay disponibles para subir a nuestra base de datos, las cuales se encuentran
  en la carpeta resources_to_upload. A continuación introducimos el nombre de la pelicula que queremos subir y esperamos a que se realice la acción. 
  **IMPORTANTE: introducir solo el nombre del archivo con el .mp4 incluido y sin poner el nombre de la carpeta.** Por ejemplo, para subir la película lightyear,
  deberá introducir "lightyear.mp4".
  2. Borrar una pelicula: primero se le pedirá que busque en el catálogo, por nombre o por tags, el vídeo que se desea eliminar, 
  y a continuación, introducir el id del archivo y esperar a que se elimine. 
  3. Renombrar una pelicula: tras buscar la película en el catálogo e introducir su id, se le pedirá el nuevo nombre del archivo que pasará a tener.
  4. Añadir tags a una pelicula: tras buscar la película en el catálogo e introducir su id, se le pedirá la lista de tags que desee añadir a la película, 
  **separados por ;**.
  5. Borrar tags a una pelicula: tras buscar la película en el catálogo e introducir su id, se le pedirá la lista de tags que desee suprimir de la película, 
  **separados por ;**.

  ### **Salir de la aplicación:**
  
  Finalmente, si pulsa la opción 8 automaticamente se sale de la aplicacion y se deja de ejecutar el cliente. Para parar el servidor se pulsa _Control+C_.
  

  