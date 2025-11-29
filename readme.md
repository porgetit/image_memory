# 📘 **Sistema de imagen 3-bit para FPGA DE1-SoC**

Este proyecto implementa un sistema completo para:

* Convertir imágenes a **3 bits por pixel (8 colores)**.
* Enviarlas mediante **UART RS232** a la FPGA.
* Almacenarlas en un **framebuffer en BRAM**.
* Visualizarlas en un monitor a través del módulo VGA.
* Modificarlas usando cursor + interruptores.

El diseño combina:

* Un **módulo de memoria en Verilog (dual-port BRAM)**.
* Un **módulo monolítico en Python (`image_sender.py`)**.
* Un **protocolo binario de comunicación simple y robusto**.
* Una **batería de pruebas Pytest** para garantizar fiabilidad.

---

# 📌 1. Módulo de memoria en FPGA (Verilog)

Este módulo almacena la imagen en formato **3-bit por píxel** en una **RAM dual-port** dentro de la FPGA.
Está pensado para integrarse con:

* El módulo UART (escritura).
* El módulo VGA (lectura).
* El módulo de cursor y edición (escritura).

---

## 🔧 **Código del módulo `image_memory.v` explicado línea por línea**

```verilog
module image_memory #(
    parameter WIDTH  = 160,             
    parameter HEIGHT = 120,             
    parameter ADDR_WIDTH = $clog2(WIDTH*HEIGHT)
)(
    input  wire                 clk,
    
    // --- Puerto A: Escritura ---
    input  wire                 we_a,  
    input  wire [ADDR_WIDTH-1:0] addr_a,
    input  wire [2:0]           data_in_a,

    // --- Puerto B: Lectura ---
    input  wire [ADDR_WIDTH-1:0] addr_b,
    output reg  [2:0]           data_out_b
);

    reg [2:0] mem [(WIDTH*HEIGHT)-1:0];

    always @(posedge clk) begin
        if (we_a)
            mem[addr_a] <= data_in_a;
    end

    always @(posedge clk) begin
        data_out_b <= mem[addr_b];
    end

endmodule
```

### ✔ Decisiones de diseño

* **Dual-port BRAM**: permite lectura VGA + escritura UART simultánea.
* **3 bits por pixel**: cumplen el requisito del proyecto (8 colores).
* **Memoria interna de FPGA (M10K)**: garantiza latencia mínima.
* **Acceso secuencial FIFO-friendly** por puerto A.
* **Acceso aleatorio** por puerto B para VGA.

### ✔ Integración con otros módulos

| Módulo       | Interacción                               |
| ------------ | ----------------------------------------- |
| UART RX      | Escribe bytes (3 bits útiles) en Puerto A |
| Cursor/Paint | Escribe sobrescribiendo píxeles           |
| VGA          | Lee píxeles por Puerto B                  |

---

# 📌 2. Módulo Python monolítico: `image_sender.py`

Este módulo:

1. Carga una imagen (.png/.jpg).
2. La convierte a 3 bits por píxel mediante cuantización RGB → paleta fija de 8 colores.
3. La redimensiona a la resolución de la FPGA.
4. Empaqueta los datos usando un protocolo binario.
5. Envía todo por UART a la FPGA.

---

## 🎨 Paleta de 8 colores (3 bits)

```
0: negro      (0, 0, 0)
1: azul       (0, 0, 255)
2: verde      (0, 255, 0)
3: cian       (0, 255, 255)
4: rojo       (255, 0, 0)
5: magenta    (255, 0, 255)
6: amarillo   (255, 255, 0)
7: blanco     (255, 255, 255)
```

El algoritmo elige el color más cercano mediante distancia Euclídea RGB.

---

## 🔌 Protocolo de comunicación PC → FPGA

El paquete enviado tiene este formato:

```
[0..3]  "IMG3"
[4..5]  ancho (big-endian)
[6..7]  alto (big-endian)
[8..N]  datos de píxel (1 byte por pixel, bits [2:0] = color)
```

Ejemplo:

| Byte | Contenido                |
| ---- | ------------------------ |
| 0–3  | "IMG3"                   |
| 4–5  | Width (2 bytes)          |
| 6–7  | Height (2 bytes)         |
| 8…   | Píxeles de 3 bits en LSB |

La FPGA solo necesita leer el LSB del byte:

```verilog
pixel_value <= uart_rx_byte[2:0];
```

---

## 🧾 Código del módulo Python (resumen)

El módulo incluye:

* Cuantización: `_quantize_color_to_palette_3bit()`
* Lectura y resize de imagen: `load_and_convert_to_3bit_indices()`
* Empaquetamiento de protocolo: `build_image_packet()`
* Envío por UART: `send_packet_over_serial()`
* CLI integrada con argparse.

Ejemplo de uso:

```bash
python image_sender.py -i foto.png -p COM3
```

---

# 📌 3. Batería de pruebas con Pytest

Las pruebas cubren:

* Distancias de color.
* Cuantización exacta y aproximada.
* Conversión de imagen → índices 3-bit.
* Empaquetado correcto del protocolo.
* Mock del puerto serial (sin hardware real).
* Mock de la CLI.

---

## 📁 Estructura recomendada

```
tests/
├── test_palette.py
├── test_image_processing.py
├── test_packet.py
├── test_serial.py
└── test_cli.py
```

---

## 🧪 Ejecución de pruebas

```bash
pytest -v
```

---

# 📌 4. Arquitectura completa del sistema

```
            +---------------------+
            |      PC / Python    |
            |  image_sender.py    |
            +----------+----------+
                       |
                       | UART (RS232)
                       |
+----------------------+-----------------------+
|                    FPGA                     |
|                                              |
|   +------------+     +------------------+    |
|   | UART RX    +---->+ image_memory.v   +---→ VGA
|   +------------+     +------------------+    |
|          ▲                 ▲                 |
| cursor   |                 |                 |
| painter  |          lectura/visualización    |
|          |                                   |
+----------+-----------------------------------+
```

