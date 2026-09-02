import pandas as pd


DUPLICATE_KEY = "CRR IDDELITO"
UPDATE_COLUMN = "ACTUALIZACIÓN"


def classify_duplicate_group(
    group: pd.DataFrame,
) -> dict:
    """
    Clasifica un conjunto de filas con el mismo CRR IDDELITO.
    """

    total_rows = len(group)
    distinct_rows = len(group.drop_duplicates())

    different_columns = [
        column
        for column in group.columns
        if group[column].nunique(dropna=False) > 1
    ]

    total_updates = group[
        UPDATE_COLUMN
    ].nunique(dropna=False)

    if distinct_rows == 1:
        classification = "DUPLICADO_EXACTO"

    elif total_updates > 1:
        classification = "VERSIONES_DIFERENTES"

    else:
        classification = "DUPLICADO_CON_DIFERENCIAS"

    return {
        "CANTIDAD_FILAS": total_rows,
        "CANTIDAD_FILAS_DISTINTAS": distinct_rows,
        "CANTIDAD_ACTUALIZACIONES": total_updates,
        "CLASIFICACION_DUPLICADO": classification,
        "COLUMNAS_CON_DIFERENCIAS": " | ".join(
            different_columns
        ),
    }


def generate_duplicate_reports(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Genera el detalle y el resumen de delitos duplicados.
    """

    duplicate_mask = dataframe.duplicated(
        subset=[DUPLICATE_KEY],
        keep=False,
    )

    duplicate_rows = dataframe.loc[
        duplicate_mask
    ].copy()

    if duplicate_rows.empty:
        empty_summary = pd.DataFrame(
            columns=[
                "CLASIFICACION_DUPLICADO",
                "CANTIDAD_GRUPOS",
                "CANTIDAD_FILAS",
            ]
        )

        return duplicate_rows, empty_summary

    group_results = []

    for crime_id, group in duplicate_rows.groupby(
        DUPLICATE_KEY,
        dropna=False,
        sort=True,
    ):
        group_result = classify_duplicate_group(group)

        group_result[DUPLICATE_KEY] = crime_id

        group_results.append(group_result)

    duplicate_groups = pd.DataFrame(group_results)

    duplicate_detail = duplicate_rows.merge(
        duplicate_groups,
        on=DUPLICATE_KEY,
        how="left",
        validate="many_to_one",
    )

    duplicate_detail = duplicate_detail.sort_values(
        by=[
            "CLASIFICACION_DUPLICADO",
            DUPLICATE_KEY,
            UPDATE_COLUMN,
        ],
        na_position="last",
    )

    duplicate_summary = (
        duplicate_groups.groupby(
            "CLASIFICACION_DUPLICADO",
            as_index=False,
            dropna=False,
        )
        .agg(
            CANTIDAD_GRUPOS=(
                DUPLICATE_KEY,
                "count",
            ),
            CANTIDAD_FILAS=(
                "CANTIDAD_FILAS",
                "sum",
            ),
        )
        .sort_values(
            by="CANTIDAD_GRUPOS",
            ascending=False,
        )
    )

    return duplicate_detail, duplicate_summary