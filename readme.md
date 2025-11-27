# Módulo de memoria para imagen de 3 bits en la FPGA DE1-SoC

Aqui se documenta el módulo `image_memory` diseñado para almacenar una imagen de **3 bits por píxel (8 colores)** dentro de la FPGA de la tarjeta **DE1-SoC**, como parte del proyecto de co-procesamiento para binarización y edición de imágenes descrito en el enunciado de Electrónica Digital. Escrito y propuesto por el profesor Ramiro Andres Barrios de la Universidad Tecnológica de Pereira en el segundo semestre de 2025.

El módulo se implementa como una **RAM dual-port**:

- Un puerto se usa principalmente para **escritura** (desde UART / lógica de edición).
- El otro puerto se usa principalmente para **lectura** (por el módulo de video VGA).

---

## 1. Código del módulo comentado línea por línea

A continuación se muestra el módulo completo con comentarios detallados **línea por línea** para entender su función y motivación.

```verilog
module image_memory #(                  // Declaración del módulo 'image_memory' con parámetros.
    parameter WIDTH  = 160,             // Parámetro: ancho de la imagen en píxeles (por defecto 160).
    parameter HEIGHT = 120,             // Parámetro: alto de la imagen en píxeles (por defecto 120).
    parameter ADDR_WIDTH = $clog2(WIDTH*HEIGHT) 
                                        // Parámetro: número de bits de dirección.
                                        // Se calcula como log2(WIDTH*HEIGHT) usando $clog2.
)(
    input  wire                 clk,    // Reloj principal del sistema. Sincroniza lecturas y escrituras.
    
    // --- Puerto A: Escritura ---
    input  wire                 we_a,   // Señal de escritura (Write Enable) del puerto A.
                                        // Cuando we_a = 1, se escribe un pixel en la memoria.
    input  wire [ADDR_WIDTH-1:0] addr_a,// Dirección de memoria para el puerto A (escritura).
    input  wire [2:0]           data_in_a,
                                        // Datos de entrada del puerto A: un pixel de 3 bits (8 colores).

    // --- Puerto B: Lectura ---
    input  wire [ADDR_WIDTH-1:0] addr_b,// Dirección de memoria para el puerto B (lectura).
    output reg  [2:0]           data_out_b
                                        // Datos de salida del puerto B: pixel leído de la memoria (3 bits).
);

    // Memoria: 3 bits por pixel
    reg [2:0] mem [(WIDTH*HEIGHT)-1:0]; // Declaración del arreglo de memoria.
                                        // 'mem' tiene WIDTH*HEIGHT posiciones.
                                        // Cada posición almacena 3 bits (un pixel).

    // Escritura en Puerto A
    always @(posedge clk) begin         // Bloque secuencial sensible al flanco positivo del reloj.
        if (we_a)                       // Si la señal de escritura está activa...
            mem[addr_a] <= data_in_a;   // ...se almacena el valor 'data_in_a' en la dirección 'addr_a'.
    end

    // Lectura en Puerto B
    always @(posedge clk) begin         // Bloque secuencial para la lectura, también sincronizado al reloj.
        data_out_b <= mem[addr_b];      // En cada flanco de subida, se lee 'mem[addr_b]'
                                        // y se asigna su valor a 'data_out_b'.
    end

endmodule                                // Fin del módulo 'image_memory'.
