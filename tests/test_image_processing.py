from PIL import Image
import image_sender

def test_load_and_convert_to_3bit_indices():
    # Crear imagen simple 2x2
    img = Image.new("RGB", (2, 2), (255, 0, 0))  # roja

    # Guardar temporalmente
    img.save("tmp_test_img.png")

    pixels, w, h = image_sender.load_and_convert_to_3bit_indices(
        "tmp_test_img.png",
        width=2,
        height=2
    )

    # Todos los píxeles deben ser rojo → índice 4
    assert pixels == [4, 4, 4, 4]
    assert w == 2
    assert h == 2
