import image_sender
import builtins
from unittest.mock import patch, MagicMock

def test_send_packet_over_serial_mocked():
    packet = b"TEST123"

    with patch("serial.Serial") as MockSerial:
        mock_serial = MagicMock()
        MockSerial.return_value.__enter__.return_value = mock_serial

        image_sender.send_packet_over_serial(packet, port="COM_TEST", baudrate=9600)

        # Verificar que se llamó a write() con el paquete
        mock_serial.write.assert_called_with(packet)

        # Verificar que flush fue llamado
        mock_serial.flush.assert_called_once()
