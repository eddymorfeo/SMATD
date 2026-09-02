from src.config import (
    DUPLICATE_DETAIL_REPORT_FILE,
    DUPLICATE_SUMMARY_REPORT_FILE,
    NULL_REPORT_FILE,
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

    print(
        "\nAnálisis finalizado correctamente."
    )