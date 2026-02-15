# Gestor de Enlaces para NVDA

Este complemento para NVDA permite gestionar enlaces web de manera eficiente, facilitando guardar, abrir, editar y eliminar enlaces a través de una interfaz sencilla y accesible. Se activa utilizando el atajo de teclado `Alt + NVDA + K` (modificable en gestos de entrada), ubicado bajo la categoría "Gestor de Enlaces".

## Forma de uso

### Añadir un Nuevo Enlace

Para añadir un nuevo enlace, sigue estos pasos:

1. Activa el panel de añadir enlaces con `Ctrl + A` o pulsando el botón "añadir enlace".
2. Escribe el título del enlace en el campo "Título".
3. Introduce la URL en el campo "URL".
4. Pulsa el botón "Guardar" para almacenar el enlace.

**Nota:** Al pulsar `Ctrl + A` cuando el panel está abierto, este se ocultará.

### Abrir un Enlace

Para abrir un enlace guardado:

- Selecciona el título del enlace en la lista y presiona `Enter` o `Espacio` para abrirlo en tu navegador predeterminado.

### Editar, Borrar, Importar y Exportar Enlaces

Para modificar o eliminar enlaces existentes:

- **Editar un Enlace**: Selecciona el enlace deseado de la lista y pulsa `Ctrl + E` o pulsa el botón "Editar enlace".
- **Borrar un Enlace**: Selecciona el enlace deseado de la lista y pulsa `Ctrl + B` o el botón "borrar enlace".
Estas acciones también se pueden hacer con el menú contextual, pulsando aplicaciones. Desde dicho menú también tenemos las opciones de exportar nuestros enlaces e importar, útil en caso de querer conservarlos.

### Añadir enlaces desde el navegador

Para añadir enlaces directamente desde tu navegador al gestor, utiliza el atajo de teclado `Alt + NVDA + K`, 2 veces, o el atajo establecido en caso de cambiarse.

### Navegación virtual de enlaces

El complemento incluye scripts de navegación virtual que permiten recorrer los enlaces y categorías guardados sin abrir la ventana del gestor. Estos scripts no tienen gesto asignado por defecto; para usarlos, asígnalos desde NVDA > Preferencias > Gestos de entrada, en la categoría "Gestor De Enlaces".

Los scripts disponibles son:

- **Enlace siguiente / Enlace anterior**: Navegan por la lista de enlaces guardados, anunciando el título y la URL de cada uno. Si previamente se seleccionó una categoría, la navegación se limita a los enlaces de esa categoría.
- **Categoría siguiente / Categoría anterior**: Navegan por las categorías disponibles, anunciando el nombre de la categoría y la cantidad de enlaces que contiene. Al cambiar de categoría, la navegación de enlaces se reinicia al inicio.

## Gestión de los Enlaces

Los enlaces se almacenan en un archivo JSON denominado `links.json` dentro de la carpeta de configuración de NVDA. Si el archivo no existe, se creará automáticamente cuando añadas tu primer enlace.

## Agradecimientos

Quiero agradecer especialmente a [José Pérez](https://github.com/JosePerezHuanca), [Angel Alcántar](https://github.com/rayo-alcantar) y a [Javi Domínguez](https://github.com/javidominguez) por su colaboración en las pruebas y mejoras del complemento.

## Registro de cambios

### Versión 0.1

- Versión inicial del complemento.

### Versión 0.5

- Corrección de errores y mejoras en la usabilidad.

### Versión 1.0

- Muchos cambios internos.
- Modificada la forma de agregar enlaces.
- Añadido el menú contextual.

### Versión 1.1
- Añadidos botones a la interfaz para hacer las acciones principales del programa
- Añadida la opción de exportar e importar el json al menú contextual
- Arreglados pequeños problemas  en los errores
- Añadidos  mensajes de traducción

### Versión 1.1.1
- Arreglado un pequeño gran problema en el complemento

### Versión 1.1.2
-  Solución de problemas

### Versión 1.1.3

-  Ahora el complemento se puede cerrar con escape.

###  Versión 1.2.0
- Nuevos atajos de teclado en la interfaz:
Control + c: copiar la URL del enlace enfocado.
Control + r: reordenar los enlaces alfabéticamente.
- Corrección de errores


###  Versión 1.5
- Compatible con NVDA 25.1
- Añadidas categorías para  los enlaces
