import image_sender
from unittest.mock import patch, MagicMock

def test_cli_main_flow():
    args = [
        "--image", "test.png",
        "--port", "COM3",
    ]

    # Mock de funciones internas
    with patch("image_sender.load_and_convert_to_3bit_indices") as mock_load, \
         patch("image_sender.build_image_packet") as mock_packet, \
         patch("image_sender.send_packet_over_serial") as mock_send:

        mock_load.return_value = ([1,2,3], 160, 120)
        mock_packet.return_value = b"DATA"

        image_sender.main(args)

        mock_load.assert_called_once()
        mock_packet.assert_called_once()
        mock_send.assert_called_once()
