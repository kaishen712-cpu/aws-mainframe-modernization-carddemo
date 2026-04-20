"""
Unit tests for cobswait.py — the Python translation of COBSWAIT.CBL.

These tests verify the wait utility correctly converts centiseconds
to seconds and handles edge cases.
"""

import unittest
from unittest.mock import patch

from cobswait import wait_centiseconds


class TestWaitCentiseconds(unittest.TestCase):
    """Tests for the wait_centiseconds function."""

    @patch("cobswait.time.sleep")
    def test_one_second(self, mock_sleep: unittest.mock.MagicMock) -> None:
        """100 centiseconds = 1.0 second."""
        wait_centiseconds(100)
        mock_sleep.assert_called_once_with(1.0)

    @patch("cobswait.time.sleep")
    def test_ten_milliseconds(self, mock_sleep: unittest.mock.MagicMock) -> None:
        """1 centisecond = 0.01 seconds."""
        wait_centiseconds(1)
        mock_sleep.assert_called_once_with(0.01)

    @patch("cobswait.time.sleep")
    def test_sixty_seconds(self, mock_sleep: unittest.mock.MagicMock) -> None:
        """6000 centiseconds = 60.0 seconds."""
        wait_centiseconds(6000)
        mock_sleep.assert_called_once_with(60.0)

    @patch("cobswait.time.sleep")
    def test_zero_centiseconds(self, mock_sleep: unittest.mock.MagicMock) -> None:
        """0 centiseconds = 0.0 seconds (no wait)."""
        wait_centiseconds(0)
        mock_sleep.assert_called_once_with(0.0)

    @patch("cobswait.time.sleep")
    def test_five_minutes(self, mock_sleep: unittest.mock.MagicMock) -> None:
        """30000 centiseconds = 300.0 seconds = 5 minutes."""
        wait_centiseconds(30000)
        mock_sleep.assert_called_once_with(300.0)

    def test_negative_raises_error(self) -> None:
        """Negative centiseconds should raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            wait_centiseconds(-1)
        self.assertIn("non-negative", str(ctx.exception))

    @patch("cobswait.time.sleep")
    def test_large_value(self, mock_sleep: unittest.mock.MagicMock) -> None:
        """Large centisecond values should be handled correctly."""
        wait_centiseconds(99999999)
        mock_sleep.assert_called_once_with(999999.99)

    @patch("cobswait.time.sleep")
    def test_fractional_seconds(self, mock_sleep: unittest.mock.MagicMock) -> None:
        """50 centiseconds = 0.5 seconds."""
        wait_centiseconds(50)
        mock_sleep.assert_called_once_with(0.5)


class TestMainFunction(unittest.TestCase):
    """Tests for the main() entry point."""

    @patch("cobswait.time.sleep")
    @patch("builtins.input", return_value="00000100")
    @patch("builtins.print")
    def test_main_reads_input(
        self,
        mock_print: unittest.mock.MagicMock,
        mock_input: unittest.mock.MagicMock,
        mock_sleep: unittest.mock.MagicMock,
    ) -> None:
        """main() should read parameter from input and wait."""
        from cobswait import main
        main()
        mock_sleep.assert_called_once_with(1.0)

    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    def test_main_empty_input(
        self,
        mock_print: unittest.mock.MagicMock,
        mock_input: unittest.mock.MagicMock,
    ) -> None:
        """main() should handle empty input gracefully."""
        from cobswait import main
        main()
        mock_print.assert_called_with("COBSWAIT: No parameter provided")

    @patch("builtins.input", return_value="ABCDEFGH")
    @patch("builtins.print")
    def test_main_invalid_input(
        self,
        mock_print: unittest.mock.MagicMock,
        mock_input: unittest.mock.MagicMock,
    ) -> None:
        """main() should handle non-numeric input gracefully."""
        from cobswait import main
        main()
        mock_print.assert_called_with("COBSWAIT: Invalid parameter: 'ABCDEFGH'")


if __name__ == "__main__":
    unittest.main()
