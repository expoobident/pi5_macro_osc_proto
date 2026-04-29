from __future__ import annotations

import unittest

from src.oscillator import Oscillator


class OscillatorTests(unittest.TestCase):
    def test_render_outputs_stay_bipolar(self) -> None:
        osc = Oscillator(sample_rate=100.0)
        osc.set_params(pitch_hz=7.0, timbre=10.0, morph=10.0, index=10.0)

        for _ in range(200):
            main, aux = osc.render()
            self.assertGreaterEqual(main, -1.0)
            self.assertLessEqual(main, 1.0)
            self.assertGreaterEqual(aux, -1.0)
            self.assertLessEqual(aux, 1.0)

    def test_triangle_and_saw_morph_generate_different_main_waveforms(self) -> None:
        triangle = Oscillator(sample_rate=100.0)
        saw = Oscillator(sample_rate=100.0)
        triangle.set_params(pitch_hz=1.0, timbre=0.0, morph=0.0, index=0.0)
        saw.set_params(pitch_hz=1.0, timbre=0.0, morph=1.0, index=0.0)

        for _ in range(25):
            triangle_main, _ = triangle.render()
            saw_main, _ = saw.render()

        self.assertAlmostEqual(triangle_main, 0.0, places=6)
        self.assertLess(saw_main, -0.4)

    def test_aux_index_blends_triangle_toward_square(self) -> None:
        triangle_aux = Oscillator(sample_rate=100.0)
        square_aux = Oscillator(sample_rate=100.0)
        triangle_aux.set_params(pitch_hz=1.0, timbre=0.0, morph=0.0, index=0.0)
        square_aux.set_params(pitch_hz=1.0, timbre=0.0, morph=0.0, index=1.0)

        _, tri_value = triangle_aux.render()
        _, square_value = square_aux.render()

        self.assertLess(tri_value, square_value)
        self.assertEqual(square_value, 1.0)


if __name__ == "__main__":
    unittest.main()
