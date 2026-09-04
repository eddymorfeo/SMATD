from src.config import (
    ADDRESS_ALIAS_CATALOG_FILE,
    ADDRESS_QUALITY_REPORT_FILE,
    DUPLICATE_DETAIL_REPORT_FILE,
    DUPLICATE_SUMMARY_REPORT_FILE,
    NORMALIZED_DATA_FILE,
    NULL_REPORT_FILE,
)
from src.address_normalization import (
    generate_address_quality_report,
    normalize_addresses,
)
from src.data_loader import load_source_data
from src.data_quality import generate_initial_profile
from src.duplicate_analysis import generate_duplicate_reports
from src.report_exporter import export_dataframe_to_csv


def show_initial_profile(profile: dict) -> None:
    """
    Muestra el resumen inicial en la consola.
    """

    print(
        f"Filas encontradas: "
        f"{profile['total_rows']:,}"
    )

    print(
        f"Columnas encontradas: "
        f"{profile['total_columns']}"
    )

    print(
        f"Casos únicos: "
        f"{profile['total_cases']:,}"
    )

    print(
        f"Delitos únicos: "
        f"{profile['total_crimes']:,}"
    )

    print(
        "Filas pertenecientes a delitos duplicados: "
        f"{profile['duplicated_crimes']:,}"
    )


def show_duplicate_summary(
    duplicate_summary,
) -> None:
    """
    Muestra el resumen de duplicados.
    """

    print("\nResumen de duplicados:")

    if duplicate_summary.empty:
        print(
            "No se encontraron delitos duplicados."
        )

        return

    print(
        duplicate_summary.to_string(
            index=False,
        )
    )


def run_analysis_pipeline() -> None:
    """
    Ejecuta el pipeline inicial de análisis.
    """

    print("Iniciando análisis de datos...")

    dataframe = load_source_data()

    profile = generate_initial_profile(
        dataframe
    )

    show_initial_profile(profile)

    export_dataframe_to_csv(
        dataframe=profile["null_summary"],
        output_file=NULL_REPORT_FILE,
        include_index=True,
    )

    print(
        f"Reporte de valores nulos generado: "
        f"{NULL_REPORT_FILE}"
    )

    duplicate_detail, duplicate_summary = (
        generate_duplicate_reports(dataframe)
    )

    export_dataframe_to_csv(
        dataframe=duplicate_detail,
        output_file=DUPLICATE_DETAIL_REPORT_FILE,
    )

    export_dataframe_to_csv(
        dataframe=duplicate_summary,
        output_file=DUPLICATE_SUMMARY_REPORT_FILE,
    )

    show_duplicate_summary(
        duplicate_summary
    )

    print(
        f"Detalle de duplicados generado: "
        f"{DUPLICATE_DETAIL_REPORT_FILE}"
    )

    print(
        f"Resumen de duplicados generado: "
        f"{DUPLICATE_SUMMARY_REPORT_FILE}"
    )

    normalized_dataframe = normalize_addresses(
        dataframe=dataframe,
        catalog_file=ADDRESS_ALIAS_CATALOG_FILE,
    )

    if len(normalized_dataframe) != len(dataframe):
        raise RuntimeError(
            "La normalización alteró la cantidad de filas: "
            f"entrada={len(dataframe):,}, "
            f"salida={len(normalized_dataframe):,}."
        )

    export_dataframe_to_csv(
        dataframe=normalized_dataframe,
        output_file=NORMALIZED_DATA_FILE,
    )

    address_quality_report = (
        generate_address_quality_report(
            normalized_dataframe
        )
    )

    export_dataframe_to_csv(
        dataframe=address_quality_report,
        output_file=ADDRESS_QUALITY_REPORT_FILE,
    )

    print(
        "Filas conservadas después de normalizar: "
        f"{len(normalized_dataframe):,}"
    )

    print(
        "Datos normalizados generados: "
        f"{NORMALIZED_DATA_FILE}"
    )

    print(
        "Reporte de normalización generado: "
        f"{ADDRESS_QUALITY_REPORT_FILE}"
    )

    print(
        "\nAnálisis finalizado correctamente."
    )
