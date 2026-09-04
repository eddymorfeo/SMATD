import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.address_normalization import normalize_addresses


class AddressNormalizationTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.catalog_file = (
            Path(self.temp_directory.name) / "aliases.csv"
        )
        self.catalog_file.write_text(
            "COMUNA_CLAVE,VALOR_ORIGEN_CLAVE,VALOR_NORMALIZADO\n"
            "*,VICUNA MACKENNA,AVENIDA VICUÑA MACKENNA\n"
            "*,AVENIDA VICUNA MACKENNA,AVENIDA VICUÑA MACKENNA\n",
            encoding="utf-8-sig",
        )

        self.dataframe = pd.DataFrame(
            {
                "REGION DELITO": [" Región Metropolitana "] * 4,
                "COMUNA DELITO": ["San Ramón"] * 4,
                "CALLE DIRECCION DELITO": [
                    "Vicuña Mackenna",
                    "Av. Vicuña Mackenna",
                    "Vicuña Mackenna con Gabriela Oriente",
                    pd.NA,
                ],
                "NUMERO DIRECCION DELITO": ["1759", "S/N", 120.0, pd.NA],
                "DEPTO DIRECCION DELITO": [pd.NA] * 4,
                "BLOCK DIRECCION DELITO": [pd.NA] * 4,
                "CONJUNTO HABITACIONAL DIRECCION DELITO": [pd.NA] * 4,
                "POBLACION DIRECCION DELITO": [pd.NA] * 4,
            }
        )

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_preserves_rows_order_and_original_values(self):
        result = normalize_addresses(
            self.dataframe,
            self.catalog_file,
        )

        self.assertEqual(len(result), len(self.dataframe))
        self.assertListEqual(result["FILA_ORIGEN"].tolist(), [1, 2, 3, 4])
        pd.testing.assert_frame_equal(
            result[self.dataframe.columns],
            self.dataframe,
        )

    def test_unifies_known_street_variants(self):
        result = normalize_addresses(
            self.dataframe,
            self.catalog_file,
        )

        self.assertEqual(
            result.loc[0, "CALLE DIRECCION DELITO NORMALIZADA"],
            "AVENIDA VICUÑA MACKENNA",
        )
        self.assertEqual(
            result.loc[1, "CALLE DIRECCION DELITO NORMALIZADA"],
            "AVENIDA VICUÑA MACKENNA",
        )
        self.assertEqual(
            result.loc[1, "DIRECCION NORMALIZACION METODO"],
            "REGLAS_FORMATO",
        )

    def test_detects_intersection_without_losing_primary_street(self):
        result = normalize_addresses(
            self.dataframe,
            self.catalog_file,
        )

        self.assertTrue(result.loc[2, "ES INTERSECCION"])
        self.assertEqual(
            result.loc[2, "CALLE SECUNDARIA NORMALIZADA"],
            "GABRIELA ORIENTE",
        )

    def test_does_not_invent_missing_data(self):
        result = normalize_addresses(
            self.dataframe,
            self.catalog_file,
        )

        self.assertTrue(
            pd.isna(
                result.loc[
                    3,
                    "CALLE DIRECCION DELITO NORMALIZADA",
                ]
            )
        )


if __name__ == "__main__":
    unittest.main()
