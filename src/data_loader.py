import pandas as pd

from src.config import EXPECTED_COLUMNS, SOURCE_FILE


def load_source_data() -> pd.DataFrame:
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo fuente: {SOURCE_FILE}"
        )

    dataframe = pd.read_excel(
        SOURCE_FILE,
        sheet_name=0,
        engine="openpyxl",
    )

    # Limpieza básica de nombres de columnas
    dataframe.columns = (
        dataframe.columns
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    validate_structure(dataframe)

    return dataframe


def validate_structure(dataframe: pd.DataFrame) -> None:
    current_columns = set(dataframe.columns)
    expected_columns = set(EXPECTED_COLUMNS)

    missing_columns = expected_columns - current_columns
    unexpected_columns = current_columns - expected_columns

    if missing_columns:
        raise ValueError(
            "Faltan columnas obligatorias: "
            + ", ".join(sorted(missing_columns))
        )

    if unexpected_columns:
        print(
            "Advertencia: se encontraron columnas adicionales: "
            + ", ".join(sorted(unexpected_columns))
        )