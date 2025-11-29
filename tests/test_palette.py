import image_sender

def test_color_distance_sq():
    assert image_sender._color_distance_sq((0,0,0), (0,0,0)) == 0
    assert image_sender._color_distance_sq((255,0,0), (0,0,0)) == 255**2

def test_quantize_exact_colors():
    # Cada color exacto debería mapear al mismo índice
    for idx, color in enumerate(image_sender.PALETTE_8_COLORS):
        assert image_sender._quantize_color_to_palette_3bit(color) == idx

def test_quantize_closest_color():
    # Un color cercano al rojo debería mapear al índice 4 (rojo)
    assert image_sender._quantize_color_to_palette_3bit((250, 10, 20)) == 4
