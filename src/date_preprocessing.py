from datetime import date, datetime

import pandas as pd


DATE_COLUMN = "FECHA DELITO"
PROCESSED_DATE_COLUMN = "FECHA DELITO PROCESADA"
VALID_DATE_COLUMN = "FECHA DELITO ES VALIDA"
FUTURE_DATE_COLUMN = "FECHA DELITO ES FUTURA"
ANALYSIS_YEAR_FLAG_COLUMN = "FECHA DELITO ES AÑO ANALISIS"
MATURITY_STATUS_COLUMN = "ESTADO MADUREZ DELITO"

MONTH_NAMES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}

WEEKDAY_NAMES = {
    1: "LUNES",
    2: "MARTES",
    3: "MIERCOLES",
    4: "JUEVES",
    5: "VIERNES",
    6: "SABADO",
    7: "DOMINGO",
}


def _normalize_analysis_date(
    analysis_date: date | datetime | pd.Timestamp | None,
) -> pd.Timestamp:
    """Devuelve la fecha de corte sin componente horario."""

    if analysis_date is None:
        return pd.Timestamp.today().normalize()

    normalized_date = pd.Timestamp(analysis_date)

    if pd.isna(normalized_date):
        raise ValueError("La fecha de análisis no es válida.")

    return normalized_date.normalize()


def _parse_crime_dates(series: pd.Series) -> pd.Series:
    """Convierte fechas mixtas de Excel usando formato día/mes/año."""

    if isinstance(series.dtype, pd.DatetimeTZDtype):
        parsed = pd.to_datetime(series, errors="coerce")
        return parsed.dt.tz_localize(None).dt.normalize()

    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(
            series,
            errors="coerce",
        ).dt.normalize()

    return pd.to_datetime(
        series,
        errors="coerce",
        dayfirst=True,
        format="mixed",
    ).dt.normalize()


def enrich_temporal_data(
    dataframe: pd.DataFrame,
    analysis_year: int,
    maturity_days: int,
    analysis_date: date | datetime | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Agrega variables temporales sin sobrescribir ni eliminar registros.

    Las columnas recibidas conservan su orden y contenido. Todas las
    variables calculadas se agregan al final del DataFrame.
    """

    if DATE_COLUMN not in dataframe.columns:
        raise ValueError(
            f"No se encontró la columna obligatoria: {DATE_COLUMN}"
        )

    if not isinstance(analysis_year, int):
        raise TypeError("El año de análisis debe ser un número entero.")

    if maturity_days < 0:
        raise ValueError(
            "Los días de madurez no pueden ser negativos."
        )

    original = dataframe.copy(deep=True)
    original_columns = list(dataframe.columns)
    enriched = dataframe.copy(deep=True)
    cutoff_date = _normalize_analysis_date(analysis_date)
    parsed_dates = _parse_crime_dates(enriched[DATE_COLUMN])
    valid_dates = parsed_dates.notna()
    future_dates = valid_dates & parsed_dates.gt(cutoff_date)
    analysis_year_dates = (
        valid_dates
        & parsed_dates.dt.year.eq(analysis_year)
    )
    days_old = (cutoff_date - parsed_dates).dt.days.astype("Int64")

    enriched[PROCESSED_DATE_COLUMN] = parsed_dates
    enriched[VALID_DATE_COLUMN] = valid_dates
    enriched[FUTURE_DATE_COLUMN] = future_dates
    enriched[ANALYSIS_YEAR_FLAG_COLUMN] = analysis_year_dates
    enriched["AÑO DELITO CALCULADO"] = (
        parsed_dates.dt.year.astype("Int64")
    )
    enriched["NUMERO MES DELITO CALCULADO"] = (
        parsed_dates.dt.month.astype("Int64")
    )
    enriched["NOMBRE MES DELITO CALCULADO"] = (
        enriched["NUMERO MES DELITO CALCULADO"]
        .map(MONTH_NAMES)
        .astype("string")
    )
    enriched["DIA MES DELITO"] = (
        parsed_dates.dt.day.astype("Int64")
    )
    enriched["NUMERO DIA SEMANA DELITO"] = (
        (parsed_dates.dt.dayofweek + 1).astype("Int64")
    )
    enriched["NOMBRE DIA SEMANA DELITO"] = (
        enriched["NUMERO DIA SEMANA DELITO"]
        .map(WEEKDAY_NAMES)
        .astype("string")
    )

    iso_calendar = parsed_dates.dt.isocalendar()
    enriched["SEMANA ISO DELITO"] = (
        iso_calendar.week.astype("Int64")
    )
    enriched["AÑO SEMANA ISO DELITO"] = (
        iso_calendar.year.astype("Int64")
    )

    start_of_week = parsed_dates - pd.to_timedelta(
        parsed_dates.dt.dayofweek.fillna(0),
        unit="D",
    )
    enriched["INICIO SEMANA DELITO"] = (
        start_of_week.where(valid_dates)
    )
    enriched["PERIODO MES DELITO"] = (
        parsed_dates.dt.strftime("%Y-%m").astype("string")
    )
    enriched["TRIMESTRE DELITO"] = (
        parsed_dates.dt.quarter.astype("Int64")
    )
    enriched["DIAS ANTIGUEDAD DELITO"] = days_old

    maturity_status = pd.Series(
        "FECHA_INVALIDA",
        index=enriched.index,
        dtype="string",
    )
    maturity_status.loc[valid_dates & ~future_dates] = "PROVISIONAL"
    maturity_status.loc[
        valid_dates
        & ~future_dates
        & days_old.ge(maturity_days)
    ] = "CONSOLIDADA"
    maturity_status.loc[future_dates] = "FECHA_FUTURA"
    enriched[MATURITY_STATUS_COLUMN] = maturity_status

    auxiliary_columns = [
        column
        for column in enriched.columns
        if column not in original_columns
    ]
    enriched = enriched[
        original_columns + auxiliary_columns
    ]

    if len(enriched) != len(original):
        raise RuntimeError(
            "La preparación temporal alteró la cantidad de filas."
        )

    pd.testing.assert_frame_equal(
        enriched[original_columns],
        original,
        check_dtype=True,
        check_names=True,
    )

    return enriched


def filter_analysis_year(
    dataframe: pd.DataFrame,
    analysis_year: int,
) -> pd.DataFrame:
    """Crea una vista con todos los registros fechados en el año indicado."""

    if PROCESSED_DATE_COLUMN not in dataframe.columns:
        raise ValueError(
            "Primero debe ejecutarse enrich_temporal_data()."
        )

    mask = (
        dataframe[PROCESSED_DATE_COLUMN]
        .dt.year
        .eq(analysis_year)
    )

    return dataframe.loc[mask].copy()


def generate_date_quality_report(
    dataframe: pd.DataFrame,
    analysis_year: int,
) -> pd.DataFrame:
    """Genera controles reconciliables sobre FECHA DELITO."""

    required_columns = {
        PROCESSED_DATE_COLUMN,
        VALID_DATE_COLUMN,
        FUTURE_DATE_COLUMN,
        MATURITY_STATUS_COLUMN,
    }
    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            "Faltan columnas temporales: "
            + ", ".join(sorted(missing_columns))
        )

    total_rows = len(dataframe)
    valid_mask = dataframe[VALID_DATE_COLUMN].fillna(False)
    year_mask = (
        dataframe[PROCESSED_DATE_COLUMN]
        .dt.year
        .eq(analysis_year)
        .fillna(False)
    )
    future_year_mask = (
        year_mask
        & dataframe[FUTURE_DATE_COLUMN].fillna(False)
    )
    statuses = dataframe[MATURITY_STATUS_COLUMN]

    metrics = [
        ("TOTAL_REGISTROS", total_rows),
        ("FECHA_DELITO_VALIDA", int(valid_mask.sum())),
        ("FECHA_DELITO_INVALIDA", int((~valid_mask).sum())),
        (f"REGISTROS_AÑO_{analysis_year}", int(year_mask.sum())),
        (
            "REGISTROS_OTROS_AÑOS",
            int((valid_mask & ~year_mask).sum()),
        ),
        (
            f"FECHAS_FUTURAS_AÑO_{analysis_year}",
            int(future_year_mask.sum()),
        ),
        (
            f"REGISTROS_PROVISIONALES_AÑO_{analysis_year}",
            int((year_mask & statuses.eq("PROVISIONAL")).sum()),
        ),
        (
            f"REGISTROS_CONSOLIDADOS_AÑO_{analysis_year}",
            int((year_mask & statuses.eq("CONSOLIDADA")).sum()),
        ),
    ]

    report = pd.DataFrame(
        metrics,
        columns=["INDICADOR", "CANTIDAD_FILAS"],
    )
    report["PORCENTAJE_TOTAL"] = (
        report["CANTIDAD_FILAS"]
        .div(total_rows if total_rows else 1)
        .mul(100)
        .round(2)
    )

    return report
