from src.config import REPORTS_DIR
from src.data_loader import load_source_data
from src.data_quality import generate_initial_profile


def main() -> None:
    print("Iniciando análisis de datos...")

    dataframe = load_source_data()
    profile = generate_initial_profile(dataframe)

    print(f"Filas encontradas: {profile['total_rows']:,}")
    print(f"Columnas encontradas: {profile['total_columns']}")
    print(f"Casos únicos: {profile['total_cases']:,}")
    print(f"Delitos únicos: {profile['total_crimes']:,}")
    print(
        "Filas pertenecientes a delitos duplicados: "
        f"{profile['duplicated_crimes']:,}"
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    output_file = REPORTS_DIR / "reporte_valores_nulos.csv"

    profile["null_summary"].to_csv(
        output_file,
        encoding="utf-8-sig",
    )

    print(f"Reporte generado: {output_file}")
    print("Análisis inicial finalizado correctamente.")


if __name__ == "__main__":
    main()