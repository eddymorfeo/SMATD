import pandas as pd


def generate_initial_profile(dataframe: pd.DataFrame) -> dict:
    """
    Genera un perfil inicial de calidad y volumen del conjunto de datos.
    """

    total_rows = len(dataframe)
    total_columns = len(dataframe.columns)

    total_cases = dataframe["CRR IDCASO"].nunique(dropna=True)
    total_crimes = dataframe["CRR IDDELITO"].nunique(dropna=True)

    duplicated_crimes = dataframe.duplicated(
        subset=["CRR IDDELITO"],
        keep=False,
    ).sum()

    null_summary = (
        dataframe.isna()
        .sum()
        .sort_values(ascending=False)
        .rename("CANTIDAD_NULOS")
        .to_frame()
    )

    if total_rows > 0:
        null_summary["PORCENTAJE_NULOS"] = (
            null_summary["CANTIDAD_NULOS"]
            .div(total_rows)
            .mul(100)
            .round(2)
        )
    else:
        null_summary["PORCENTAJE_NULOS"] = 0.0

    null_summary["CANTIDAD_INFORMADOS"] = (
        total_rows - null_summary["CANTIDAD_NULOS"]
    )

    null_summary.index.name = "COLUMNA"

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "total_cases": total_cases,
        "total_crimes": total_crimes,
        "duplicated_crimes": duplicated_crimes,
        "null_summary": null_summary,
    }