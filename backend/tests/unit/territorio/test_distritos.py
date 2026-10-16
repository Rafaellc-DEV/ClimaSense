"""Porte dos 6 testes de Desktop/AVD/tests/test_distritos.py, com as MESMAS asserções (RF-13.6)."""

import copy
import unittest

from climasense.territorio.carga import carregar_arquivos, corrigir_vinculos, enriquecer_distritos
from climasense.territorio.geometria import area_km2


class DadosDistritosTest(unittest.TestCase):
    def test_base_oficial_tem_oito_distritos_e_94_bairros(self):
        geo, bairros = carregar_arquivos()
        result = enriquecer_distritos(geo, bairros)
        self.assertEqual(len(result["features"]), 8)
        self.assertEqual(sum(f["properties"]["quantidade_bairros"] for f in result["features"]), 94)
        self.assertEqual(
            [f["properties"]["quantidade_bairros"] for f in result["features"]],
            [11, 18, 16, 12, 16, 5, 4, 12],
        )
        self.assertTrue(all(f["properties"]["area_km2"] > 0 for f in result["features"]))

    def test_codigo_textual_e_numerico_se_relacionam(self):
        geo, bairros = carregar_arquivos()
        geo["features"][0]["properties"]["cdistscodi"] = "1"
        result = enriquecer_distritos(geo, bairros)
        self.assertEqual(result["features"][0]["properties"]["nome_distrito"], "DS I")

    def test_distrito_sem_correspondencia_e_rejeitado(self):
        geo, bairros = carregar_arquivos()
        geo["features"][0]["properties"]["cdistscodi"] = 99
        with self.assertRaises(ValueError):
            enriquecer_distritos(geo, bairros)

    def test_bairros_duplicados_nao_inflam_indicador(self):
        geo, bairros = carregar_arquivos()
        bairros.append(copy.deepcopy(bairros[0]))
        result = enriquecer_distritos(geo, bairros)
        self.assertEqual(result["features"][0]["properties"]["quantidade_bairros"], 11)

    def test_area_desconta_buracos_independente_da_orientacao(self):
        outer = [[-35, -8], [-34.99, -8], [-34.99, -8.01], [-35, -8.01], [-35, -8]]
        hole = [[-34.998, -8.002], [-34.992, -8.002], [-34.992, -8.008], [-34.998, -8.008], [-34.998, -8.002]]
        full = area_km2({"type": "Polygon", "coordinates": [outer]})
        cut = area_km2({"type": "Polygon", "coordinates": [outer, hole]})
        reverse = area_km2({"type": "Polygon", "coordinates": [outer, list(reversed(hole))]})
        self.assertGreater(cut, 0)
        self.assertLess(cut, full)
        self.assertAlmostEqual(cut, reverse)

    def test_validacao_corrige_vii_viii_e_preserva_csv_original(self):
        geo, bairros = carregar_arquivos()
        original = copy.deepcopy(bairros)
        corrected = corrigir_vinculos(bairros)
        result = enriquecer_distritos(geo, corrected)
        by_code = {f["properties"]["cdistscodi"]: f["properties"] for f in result["features"]}
        self.assertEqual(bairros, original)
        self.assertEqual(by_code[7]["quantidade_bairros"], 13)
        self.assertEqual(by_code[8]["quantidade_bairros"], 3)
        self.assertIn("Brejo de Beberibe", by_code[7]["bairros"])
        self.assertIn("Guabiraba", by_code[7]["bairros"])
        self.assertEqual(by_code[8]["bairros"], ["Cohab", "Ibura", "Jordao"])
        self.assertEqual(sum(p["quantidade_bairros"] for p in by_code.values()), 94)
