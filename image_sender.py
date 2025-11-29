"""
image_sender.py

Módulo monolítico para:
1. Cargar una imagen desde archivo.
2. Redimensionarla a la resolución objetivo de la FPGA.
3. Cuantizarla a 3 bits por píxel (8 colores).
4. Empaquetar los píxeles y enviarlos por un puerto serie (RS232/UART)
   hacia el coprocesador implementado en la FPGA.

Dependencias:
    - Pillow (PIL)   -> pip install pillow
    - pyserial       -> pip install pyserial

Uso rápido desde consola:
    python image_sender.py --image entrada.png --port COM3 --baud 115200
"""

import argparse
import sys
from typing import List, Tuple

from PIL import Image   # Biblioteca para manipulación de imágenes
import serial           # Biblioteca para comunicación serial (pyserial)


# ---------------------------------------------------------------------------
# Parámetros por defecto del proyecto (ajústalos según tu diseño en FPGA)
# ---------------------------------------------------------------------------

DEFAULT_WIDTH = 160       # Ancho de la imagen objetivo
DEFAULT_HEIGHT = 120      # Alto de la imagen objetivo
DEFAULT_BAUDRATE = 115200 # Velocidad de transmisión por puerto serie
DEFAULT_MAGIC = b"IMG3"   # Identificador de protocolo para imágenes de 3 bits


# ---------------------------------------------------------------------------
# Paleta de 8 colores (3 bits) y lógica de cuantización
# ---------------------------------------------------------------------------

# Paleta fija de 8 colores (R, G, B)
PALETTE_8_COLORS: List[Tuple[int, int, int]] = [
    (0,   0,   0),   # 0: negro
    (0,   0, 255),   # 1: azul
    (0, 255,   0),   # 2: verde
    (0, 255, 255),   # 3: cian
    (255, 0,   0),   # 4: rojo
    (255, 0, 255),   # 5: magenta
    (255, 255, 0),   # 6: amarillo
    (255, 255, 255), # 7: blanco
]


def _color_distance_sq(c1: Tuple[int, int, int],
                       c2: Tuple[int, int, int]) -> int:
    """
    Calcula la distancia euclídea al cuadrado entre dos colores RGB.

    Usamos la distancia al cuadrado para evitar raíces cuadradas, lo que
    hace el cálculo más eficiente y suficiente para comparaciones.
    """
    dr = c1[0] - c2[0]
    dg = c1[1] - c2[1]
    db = c1[2] - c2[2]
    return dr * dr + dg * dg + db * db


def _quantize_color_to_palette_3bit(rgb: Tuple[int, int, int]) -> int:
    """
    Recibe un color RGB (R, G, B) y devuelve el índice (0–7) del color
    más cercano en la paleta de 8 colores.

    El índice resultante cabe en 3 bits.
    """
    best_index = 0
    best_dist = None

    for idx, pal_color in enumerate(PALETTE_8_COLORS):
        dist = _color_distance_sq(rgb, pal_color)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_index = idx

    return best_index  # Valor entre 0 y 7


# ---------------------------------------------------------------------------
# Manejo de la imagen: carga, reescalado y cuantización a 3 bits
# ---------------------------------------------------------------------------

def load_and_convert_to_3bit_indices(
    image_path: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT
) -> Tuple[List[int], int, int]:
    """
    Carga una imagen desde 'image_path', la convierte a formato RGB,
    la redimensiona a (width, height) y cuantiza cada píxel a un índice
    de 3 bits (0–7) usando la paleta PALETTE_8_COLORS.

    Devuelve:
        (pixel_indices, width, height)
    donde pixel_indices es una lista de enteros en el rango 0–7, de
    tamaño width*height, recorridos en orden fila-major (row-major):
        y = 0...height-1
            x = 0...width-1
    """
    # Cargar la imagen con Pillow
    img = Image.open(image_path)

    # Asegurar formato RGB (descartamos canal alfa, si existe)
    img = img.convert("RGB")

    # Redimensionar a la resolución objetivo del framebuffer en la FPGA
    img = img.resize((width, height), Image.BILINEAR)

    pixel_indices: List[int] = []

    # Recorremos la imagen fila por fila
    for y in range(height):
        for x in range(width):
            rgb = img.getpixel((x, y))
            idx = _quantize_color_to_palette_3bit(rgb)
            pixel_indices.append(idx)

    return pixel_indices, width, height


# ---------------------------------------------------------------------------
# Empaquetado de píxeles y protocolo de transmisión
# ---------------------------------------------------------------------------

def pack_pixels_1byte_per_pixel(pixel_indices: List[int]) -> bytes:
    """
    Empaqueta la lista de índices de píxel (0–7) en un buffer de bytes.

    Estrategia simple: 1 byte por pixel.
    - Solo usamos los 3 bits menos significativos de cada byte.
    - Esto facilita el diseño en la FPGA (cada byte recibido -> mem[addr] = byte[2:0])

    Ejemplo:
        idx = 5 (0b101) -> byte = 0x05
    """
    return bytes((idx & 0x07 for idx in pixel_indices))


def build_image_packet(
    pixel_indices: List[int],
    width: int,
    height: int,
    magic: bytes = DEFAULT_MAGIC
) -> bytes:
    """
    Construye el paquete completo a enviar por el puerto serie:

        [ MAGIC (4 bytes) ]
        [ WIDTH (2 bytes, big-endian) ]
        [ HEIGHT (2 bytes, big-endian) ]
        [ PIXEL_DATA (width * height bytes, 1 byte por píxel, LSB = índice 3 bits) ]

    Este protocolo debe ser implementado en la FPGA para reconstruir
    los 3 bits de cada píxel desde los 3 bits menos significativos
    de cada byte recibido.
    """
    if len(magic) != 4:
        raise ValueError("La cadena MAGIC debe tener exactamente 4 bytes.")

    header = bytearray()
    header.extend(magic)
    header.extend(width.to_bytes(2, byteorder="big", signed=False))
    header.extend(height.to_bytes(2, byteorder="big", signed=False))

    pixels_bytes = pack_pixels_1byte_per_pixel(pixel_indices)

    return bytes(header) + pixels_bytes


# ---------------------------------------------------------------------------
# Envío por puerto serie
# ---------------------------------------------------------------------------

def send_packet_over_serial(
    packet: bytes,
    port: str,
    baudrate: int = DEFAULT_BAUDRATE,
    timeout: float = 2.0
) -> None:
    """
    Envía el 'packet' binario a través del puerto serie indicado.

    Parámetros:
        - packet: bytes con el paquete completo (header + datos).
        - port: nombre del puerto serie (ej: 'COM3' en Windows, '/dev/ttyUSB0' en Linux).
        - baudrate: velocidad de transmisión (bit/s).
        - timeout: tiempo máximo de espera para operaciones de E/S.

    El lado de la FPGA debe estar escuchando el UART con la misma
    configuración (baudrate, formato 8-N-1 típico).
    """
    try:
        with serial.Serial(port=port, baudrate=baudrate, timeout=timeout) as ser:
            ser.write(packet)
            ser.flush()
            # Opcional: podrías implementar aquí un protocolo de respuesta
            # (por ejemplo, que la FPGA retorne un byte de ACK).
    except serial.SerialException as exc:
        print(f"Error al abrir o usar el puerto serie {port}: {exc}")
        raise


# ---------------------------------------------------------------------------
# Interfaz de línea de comandos (CLI)
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    """
    Parseo de argumentos de línea de comandos.
    Permite usar el módulo como script ejecutable.

    Ejemplo:
        python image_sender.py --image img.png --port COM3 --baud 115200
    """
    parser = argparse.ArgumentParser(
        description="Convierte una imagen a 3 bits y la envía vía puerto serie a la FPGA."
    )
    parser.add_argument(
        "--image", "-i",
        required=True,
        help="Ruta al archivo de imagen de entrada (PNG, JPG, etc.)."
    )
    parser.add_argument(
        "--port", "-p",
        required=True,
        help="Nombre del puerto serie (ej: COM3, /dev/ttyUSB0)."
    )
    parser.add_argument(
        "--baud", "-b",
        type=int,
        default=DEFAULT_BAUDRATE,
        help=f"Baudrate para el puerto serie (por defecto {DEFAULT_BAUDRATE})."
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=DEFAULT_WIDTH,
        help=f"Ancho de la imagen destino (por defecto {DEFAULT_WIDTH})."
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=DEFAULT_HEIGHT,
        help=f"Alto de la imagen destino (por defecto {DEFAULT_HEIGHT})."
    )
    return parser.parse_args(argv)


def main(argv=None):
    """
    Punto de entrada principal cuando se ejecuta como script.

    Flujo:
        1. Lee argumentos de línea de comandos.
        2. Carga y convierte la imagen a índices de 3 bits.
        3. Construye el paquete binario según el protocolo.
        4. Lo envía por el puerto serie indicado.
    """
    args = parse_args(argv)

    print(f"[INFO] Cargando y procesando imagen: {args.image}")
    pixel_indices, width, height = load_and_convert_to_3bit_indices(
        args.image,
        width=args.width,
        height=args.height,
    )

    print(f"[INFO] Imagen convertida a {width}x{height} píxeles, 3 bits por píxel.")
    print(f"[INFO] Construyendo paquete para envío serie...")
    packet = build_image_packet(pixel_indices, width, height)

    print(f"[INFO] Enviando {len(packet)} bytes al puerto {args.port} @ {args.baud} baud.")
    send_packet_over_serial(packet, port=args.port, baudrate=args.baud)
    print("[INFO] Envío completado.")


if __name__ == "__main__":
    main(sys.argv[1:])
