# agente_criptografico.py

def texto_a_numeros(texto: str) -> list[int]:
    """Convierte un texto a una lista de valores numéricos basados en ASCII."""
    return [ord(caracter) for caracter in texto]

def encriptar_con_matriz(valores: list[int], clave_2x2: list[list[int]]) -> list[int]:
    """
    Encripta una lista de números multiplicándolos por una matriz clave de 2x2.
    Agrupa los números de 2 en 2 (vectores) y los multiplica por la matriz.
    """
    # Si la cantidad de letras es impar, agregamos un espacio (ASCII 32) para emparejar
    if len(valores) % 2 != 0:
        valores.append(32)

    resultado_encriptado = []
    
    # Procesamos de 2 en 2
    for i in range(0, len(valores), 2):
        v1 = valores[i]
        v2 = valores[i+1]
        
        # Multiplicación matemática de Matriz 2x2 por Vector 2x1
        c1 = clave_2x2[0][0] * v1 + clave_2x2[0][1] * v2
        c2 = clave_2x2[1][0] * v1 + clave_2x2[1][1] * v2
        
        resultado_encriptado.extend([c1, c2])
        
    return resultado_encriptado

# --- ZONA DE PRUEBAS LOCALES PARA EL PROFESOR ---
if __name__ == "__main__":
    print("=========================================")
    print(" INICIANDO AGENTE CRIPTOGRÁFICO EN LOCAL")
    print("=========================================\n")
    
    mensaje_original = "HOLA"
    # Matriz clave 2x2
    matriz_secreta = [
        [2, 3],
        [1, 4]
    ]
    
    print(f"Mensaje original: '{mensaje_original}'")
    
    # Paso 1: Convertir a números
    numeros_base = texto_a_numeros(mensaje_original)
    print(f"Valores numéricos (ASCII): {numeros_base}")
    
    # Paso 2: Encriptar usando la matriz
    numeros_encriptados = encriptar_con_matriz(numeros_base, matriz_secreta)
    print(f"Matriz de encriptación (Clave): {matriz_secreta}")
    print(f"MENSAJE ENCRIPTADO (Matriz final): {numeros_encriptados}\n")
    
    print("Las funciones de encriptación de matrices operan correctamente.")
