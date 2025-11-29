import image_sender

def test_pack_pixels_1byte_per_pixel():
    data = [0, 1, 2, 7]
    packed = image_sender.pack_pixels_1byte_per_pixel(data)
    assert packed == bytes([0, 1, 2, 7])

def test_build_image_packet_structure():
    pixels = [3, 4, 5]
    width, height = 1, 3
    packet = image_sender.build_image_packet(pixels, width, height)

    # Debe iniciar con 'IMG3'
    assert packet[0:4] == b'IMG3'

    # Ancho y alto
    assert packet[4:6] == width.to_bytes(2, 'big')
    assert packet[6:8] == height.to_bytes(2, 'big')

    # Datos de píxel
    assert packet[8:] == bytes([3, 4, 5])
