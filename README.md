# Gestor de Enlaces para NVDA

Este complemento para NVDA permite gestionar enlaces web de manera eficiente, permitiendo guardar, abrir, editar y eliminar enlaces a través de una interfaz sencilla y accesible que se despliega con el atajo de teclado alt + NVDA + K (modificable en gestos de entrada) bajo la categoría gestor de enlaces.

## Forma de uso

### Añadir un Nuevo Enlace

Para añadir un nuevo enlace, sigue estos pasos:

1. Activa el panel de añadir enlaces con `Ctrl + A`.
2. Escribe el título del enlace en el campo "Título".
3. Escribe la URL en el campo "URL".
4. Pulsa el botón "Guardar" para almacenar el enlace.

**Nota:** Al pulsar `Ctrl + A` cuando el panel está abierto, este se ocultará.

### Abrir un Enlace

Para abrir un enlace guardado:

- Selecciona el título del enlace en la lista y presiona `Enter` o `Espacio` para abrirlo en tu navegador predeterminado.

### Editar y Borrar Enlaces

Para modificar o eliminar enlaces existentes:

- **Editar un Enlace**: Selecciona el enlace deseado de la lista y pulsa `Ctrl + E`.
- **Borrar un Enlace**: Selecciona el enlace deseado de la lista y pulsa `Ctrl + B`.

## Gestión de los Enlaces

Los enlaces se almacenan en un archivo JSON denominado `links.json` dentro de la carpeta de configuración de NVDA. Si el archivo no existe, se creará automáticamente cuando añadas tu primer enlace.

## Agradecimientos

Queremos agradecer especialmente a yares y [Angel Alcántar](https://github.com/rayo-alcantar) por su colaboración en las pruebas y mejoras del complemento.

## Registro de cambios

### Versión 0.1

- Lanzamiento inicial del complemento.

### Versión 0.5

- Corrección de errores y mejoras en la usabilidad.