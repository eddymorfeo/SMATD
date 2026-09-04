import unittest

import pandas as pd

from src.date_preprocessing import (
    enrich_temporal_data,
    filter_analysis_year,
    generate_date_quality_report,
)


class DatePreprocessingTest(unittest.TestCase):
    def setUp(self):
        self.analysis_date = pd.Timestamp("2026-09-04")
        self.dataframe = pd.DataFrame(
            {
                "CRR IDDELITO": [101, 102, 103, 104, 105],
                "FECHA DELITO": [
                    "15-01-2026",
                    "25-08-2026",
                    "20-10-2026",
                    "31-12-2025",
                    "FECHA INVALIDA",
                ],
                "VALOR ORIGINAL": ["A", "B", "C", "D", "E"],
            }
        )

    def _enrich(self) -> pd.DataFrame:
        return enrich_temporal_data(
            dataframe=self.dataframe,
            analysis_year=2026,
            maturity_days=21,
            analysis_date=self.analysis_date,
        )

    def test_preserves_rows_order_and_original_columns(self):
        result = self._enrich()

        self.assertEqual(len(result), len(self.dataframe))
        self.assertListEqual(
            list(result.columns[: len(self.dataframe.columns)]),
            list(self.dataframe.columns),
        )
        pd.testing.assert_frame_equal(
            result[self.dataframe.columns],
            self.dataframe,
        )

    def test_filters_all_2026_records_including_future_dates(self):
        result = self._enrich()
        result_2026 = filter_analysis_year(result, 2026)

        self.assertListEqual(
            result_2026["CRR IDDELITO"].tolist(),
            [101, 102, 103],
        )
        self.assertTrue(
            result_2026.loc[
                result_2026["CRR IDDELITO"].eq(103),
                "FECHA DELITO ES FUTURA",
            ].iloc[0]
        )

    def test_generates_expected_temporal_fields(self):
        result = self._enrich()
        row = result.loc[result["CRR IDDELITO"].eq(101)].iloc[0]

        self.assertEqual(row["AÑO DELITO CALCULADO"], 2026)
        self.assertEqual(row["NUMERO MES DELITO CALCULADO"], 1)
        self.assertEqual(row["NOMBRE MES DELITO CALCULADO"], "ENERO")
        self.assertEqual(row["DIA MES DELITO"], 15)
        self.assertEqual(row["NOMBRE DIA SEMANA DELITO"], "JUEVES")
        self.assertEqual(row["PERIODO MES DELITO"], "2026-01")

    def test_classifies_maturity_without_removing_future_dates(self):
        result = self._enrich().set_index("CRR IDDELITO")

        self.assertEqual(
            result.loc[101, "ESTADO MADUREZ DELITO"],
            "CONSOLIDADA",
        )
        self.assertEqual(
            result.loc[102, "ESTADO MADUREZ DELITO"],
            "PROVISIONAL",
        )
        self.assertEqual(
            result.loc[103, "ESTADO MADUREZ DELITO"],
            "FECHA_FUTURA",
        )
        self.assertEqual(
            result.loc[105, "ESTADO MADUREZ DELITO"],
            "FECHA_INVALIDA",
        )

    def test_quality_report_reconciles_total_rows(self):
        result = self._enrich()
        report = generate_date_quality_report(result, 2026)
        metrics = report.set_index("INDICADOR")["CANTIDAD_FILAS"]

        self.assertEqual(metrics["TOTAL_REGISTROS"], 5)
        self.assertEqual(metrics["FECHA_DELITO_VALIDA"], 4)
        self.assertEqual(metrics["FECHA_DELITO_INVALIDA"], 1)
        self.assertEqual(metrics["REGISTROS_AÑO_2026"], 3)
        self.assertEqual(metrics["FECHAS_FUTURAS_AÑO_2026"], 1)


if __name__ == "__main__":
    unittest.main()
