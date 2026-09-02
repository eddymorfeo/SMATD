from pathlib import Path

import pandas as pd


def export_dataframe_to_csv(
    dataframe: pd.DataFrame,
    output_file: Path,
    include_index: bool = False,
) -> None:
    """
    Exporta un DataFrame a CSV usando codificación compatible con Excel.
    """

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        output_file,
        index=include_index,
        encoding="utf-8-sig",
    )