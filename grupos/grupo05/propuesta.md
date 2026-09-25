# Propuesta de Proyecto MCP: Agente Criptográfico
##1. Curso y Tema Elegido
**Tema:** Encriptación de datos utilizando álgebra lineal (Cifrado de Hill por matrices).
## 2. Acciones del Agente MCP
Nuestro agente actuará como un asistente de seguridad y será capaz de ejecutar las siguientes herramientas mediante el Model Context Protocol:
* **Convertir texto:** Transformar mensajes de texto plano a secuencias numéricas (ASCII).
* **Encriptar datos:** Multiplicar vectores numéricos por una matriz clave (ej. 2x2) proporcionada por el usuario para generar un mensaje cifrado.
* **Procesar respuestas:** Entregarle al usuario la matriz cifrada final de forma clara y explicada.
## 3. División de Tareas (Grupo 05)
1. **Franco Solimano:** Desarrollo del código local base y la lógica matemática pura en Python.
2. **[Nombre 2]:** Envolver las funciones de Python con la librería MCP (FastMCP) para exponerlas como herramientas.
3. **[Nombre 3]:** Diseño de instrucciones (*System Prompts*) para que la IA sepa cuándo y cómo usar la herramienta matemática.
4. **[Nombre 4]:** Control de calidad (Testing), validación de datos y manejo de errores (ej. evitar que fallen matrices de tamaños incorrectos).
5. **[Nombre 5]:** Preparación del entorno de despliegue en la nube (Docker / Portainer).
6. **[Nombre 6]:** Documentación técnica final y revisión/aprobación de los Pull Requests grupales.
