import re
import unicodedata
from pathlib import Path

import pandas as pd


ADDRESS_COLUMNS = [
    "REGION DELITO",
    "COMUNA DELITO",
    "CALLE DIRECCION DELITO",
    "NUMERO DIRECCION DELITO",
    "DEPTO DIRECCION DELITO",
    "BLOCK DIRECCION DELITO",
    "CONJUNTO HABITACIONAL DIRECCION DELITO",
    "POBLACION DIRECCION DELITO",
]

TEXT_ADDRESS_COLUMNS = [
    "REGION DELITO",
    "COMUNA DELITO",
    "DEPTO DIRECCION DELITO",
    "BLOCK DIRECCION DELITO",
    "CONJUNTO HABITACIONAL DIRECCION DELITO",
    "POBLACION DIRECCION DELITO",
]

STREET_COLUMN = "CALLE DIRECCION DELITO"
NUMBER_COLUMN = "NUMERO DIRECCION DELITO"

ROAD_TYPE_PATTERNS = [
    (r"^(?:AVENIDA|AVDA|AV)\.?\s+", "AVENIDA"),
    (r"^(?:PASAJE|PSJE|PJE)\.?\s+", "PASAJE"),
    (r"^(?:CALLE|CL)\.?\s+", "CALLE"),
    (r"^(?:CAMINO|CAM)\.?\s+", "CAMINO"),
    (r"^(?:CARRETERA|CTRA)\.?\s+", "CARRETERA"),
    (r"^(?:RUTA|RTE)\.?\s+", "RUTA"),
]

INTERSECTION_PATTERN = re.compile(
    r"\s+(?:CON|ESQUINA(?:\s+CON)?|INTERSECCION(?:\s+CON)?)\s+|\s+/\s+",
    flags=re.IGNORECASE,
)


def _is_missing(value) -> bool:
    return pd.isna(value) or not str(value).strip()


def _clean_text(value):
    """Estandariza formato sin completar información inexistente."""

    if _is_missing(value):
        return pd.NA

    text = unicodedata.normalize("NFC", str(value))
    text = text.upper().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([,;])\s*", r"\1 ", text)

    return text.strip(" ,;")


def _comparison_key(value):
    """Genera una llave técnica sin tildes para comparar variantes."""

    cleaned = _clean_text(value)

    if pd.isna(cleaned):
        return pd.NA

    key = unicodedata.normalize("NFKD", cleaned)
    key = "".join(
        character
        for character in key
        if not unicodedata.combining(character)
    )
    key = re.sub(r"[^A-Z0-9]+", " ", key)

    normalized_key = re.sub(
    r"\s+",
    " ",
    key,
    ).strip()

    return normalized_key or pd.NA


def _extract_road_type(value) -> tuple[object, object]:
    cleaned = _clean_text(value)

    if pd.isna(cleaned):
        return pd.NA, pd.NA

    for pattern, road_type in ROAD_TYPE_PATTERNS:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            street_name = re.sub(
                pattern,
                "",
                cleaned,
                count=1,
                flags=re.IGNORECASE,
            ).strip()

            return road_type, street_name or pd.NA

    return pd.NA, cleaned


def _normalize_number(value):
    """Normaliza el número sin eliminar separadores significativos."""

    if _is_missing(value):
        return pd.NA

    original_text = _clean_text(value)
    comparison_text = _comparison_key(value)

    if comparison_text in {
        "SN",
        "S N",
        "SIN NUMERO",
        "SIN NUM",
    }:
        return "S/N"

    if re.fullmatch(r"\d+\.0", str(value).strip()):
        return str(value).strip()[:-2]

    normalized_number = re.sub(
        r"\s+",
        "",
        str(original_text),
    )
    normalized_number = re.sub(
        r"[^A-Z0-9/\-]",
        "",
        normalized_number,
    )

    return normalized_number or pd.NA


def _load_alias_catalog(catalog_file: Path) -> dict:
    """Carga equivalencias de calles revisadas y aprobadas."""

    if not catalog_file.exists():
        return {}

    catalog = pd.read_csv(
        catalog_file,
        dtype="string",
        encoding="utf-8-sig",
    )

    required = {
        "COMUNA_CLAVE",
        "VALOR_ORIGEN_CLAVE",
        "VALOR_NORMALIZADO",
    }

    missing = required - set(catalog.columns)

    if missing:
        raise ValueError(
            "El catálogo de direcciones no contiene: "
            + ", ".join(sorted(missing))
        )

    aliases: dict[tuple[str, str], str] = {}

    for row in catalog.itertuples(index=False):
        if (
            pd.isna(row.COMUNA_CLAVE)
            or pd.isna(row.VALOR_ORIGEN_CLAVE)
            or pd.isna(row.VALOR_NORMALIZADO)
        ):
            continue

        commune_key = (
            "*"
            if str(row.COMUNA_CLAVE).strip() == "*"
            else _comparison_key(row.COMUNA_CLAVE)
        )
        street_key = _comparison_key(row.VALOR_ORIGEN_CLAVE)
        normalized_value = _clean_text(row.VALOR_NORMALIZADO)
        key = (commune_key, street_key)

        if (
            key in aliases
            and aliases[key] != normalized_value
        ):
            raise ValueError(
                "Existen equivalencias contradictorias "
                f"para la clave {key}."
            )

        aliases[key] = normalized_value

    return aliases


def _build_territorial_key(
    commune,
    street_key,
    number=None,
):
    """Construye una llave territorial sin inventar información."""

    normalized_commune = _comparison_key(commune)
    normalized_street = _comparison_key(street_key)

    if (
        pd.isna(normalized_commune)
        or pd.isna(normalized_street)
    ):
        return pd.NA

    components = [
        str(normalized_commune),
        str(normalized_street),
    ]

    if not _is_missing(number):
        components.append(str(number))

    return "|".join(components)


def _normalize_street_row(
    commune,
    street,
    aliases: dict,
) -> dict:
    cleaned = _clean_text(street)

    if pd.isna(cleaned):
        return {
            "TIPO VIA NORMALIZADO": pd.NA,
            "CALLE DIRECCION DELITO NORMALIZADA": pd.NA,
            "CALLE SECUNDARIA NORMALIZADA": pd.NA,
            "CALLE CLAVE AGRUPACION": pd.NA,
            "ES INTERSECCION": False,
            "DIRECCION NORMALIZACION METODO": "SIN_DATO",
            "DIRECCION NORMALIZACION CONFIANZA": "NO_APLICA",
            "DIRECCION REQUIERE REVISION": False,
        }

    parts = INTERSECTION_PATTERN.split(cleaned, maxsplit=1)
    primary = parts[0]
    secondary = parts[1] if len(parts) == 2 else pd.NA
    road_type, street_name = _extract_road_type(primary)

    commune_key = _comparison_key(commune)
    street_key = _comparison_key(primary)
    alias = aliases.get((commune_key, street_key))
    alias = alias or aliases.get(("*", street_key))

    if alias:
        normalized_street = alias
        alias_road_type, alias_name = _extract_road_type(alias)
        road_type = alias_road_type
        street_name = alias_name
        method = "CATALOGO_EQUIVALENCIAS"
        confidence = "ALTA"
    else:
        normalized_street = (
            f"{road_type} {street_name}"
            if not pd.isna(road_type)
            else street_name
        )
        method = "REGLAS_FORMATO"
        confidence = "MEDIA"

    key = _comparison_key(street_name)
    requires_review = bool(
        confidence != "ALTA"
        and (
            pd.isna(key)
            or len(str(key)) < 4
            or re.search(
                r"\b(?:SIN NOMBRE|DESCONOCID[AO])\b",
                str(key),
            )
        )
    )

    return {
        "TIPO VIA NORMALIZADO": road_type,
        "CALLE DIRECCION DELITO NORMALIZADA": normalized_street,
        "CALLE SECUNDARIA NORMALIZADA": _clean_text(secondary),
        "CALLE CLAVE AGRUPACION": key,
        "ES INTERSECCION": len(parts) == 2,
        "DIRECCION NORMALIZACION METODO": method,
        "DIRECCION NORMALIZACION CONFIANZA": confidence,
        "DIRECCION REQUIERE REVISION": requires_review,
    }


def normalize_addresses(
    dataframe: pd.DataFrame,
    catalog_file: Path,
) -> pd.DataFrame:
    """
    Agrega campos normalizados sin eliminar, ordenar ni sobrescribir filas.
    """

    missing_columns = set(ADDRESS_COLUMNS) - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            "Faltan columnas de dirección: "
            + ", ".join(sorted(missing_columns))
        )

    original = dataframe.copy(deep=True)
    original_columns = list(dataframe.columns)

    normalized = dataframe.copy(deep=True)

    normalized["FILA_ORIGEN"] = range(
        1,
        len(normalized) + 1,
    )

    for column in TEXT_ADDRESS_COLUMNS:
        normalized[f"{column} NORMALIZADA"] = (
            normalized[column].map(_clean_text)
        )

    normalized[f"{NUMBER_COLUMN} NORMALIZADA"] = (
        normalized[NUMBER_COLUMN].map(_normalize_number)
    )

    aliases = _load_alias_catalog(catalog_file)
    street_results = pd.DataFrame(
        [
            _normalize_street_row(commune, street, aliases)
            for commune, street in zip(
                normalized["COMUNA DELITO"],
                normalized[STREET_COLUMN],
            )
        ],
        index=normalized.index,
    )

    normalized = pd.concat(
        [normalized, street_results],
        axis="columns",
    )

    normalized["CALLE CLAVE TERRITORIAL"] = [
        _build_territorial_key(
            commune=commune,
            street_key=street_key,
        )
        for commune, street_key in zip(
            normalized["COMUNA DELITO NORMALIZADA"],
            normalized["CALLE CLAVE AGRUPACION"],
        )
    ]

    normalized["DIRECCION CLAVE TERRITORIAL"] = [
        _build_territorial_key(
            commune=commune,
            street_key=street_key,
            number=number,
        )
        for commune, street_key, number in zip(
            normalized["COMUNA DELITO NORMALIZADA"],
            normalized["CALLE CLAVE AGRUPACION"],
            normalized[
                "NUMERO DIRECCION DELITO NORMALIZADA"
            ],
        )
    ]

    auxiliary_columns = [
        column
        for column in normalized.columns
        if column not in original_columns
    ]

    normalized = normalized[
        original_columns + auxiliary_columns
    ]

    if len(normalized) != len(original):
        raise RuntimeError("Se alteró la cantidad de filas.")

    pd.testing.assert_frame_equal(
        normalized[original.columns],
        original,
        check_dtype=True,
        check_names=True,
    )

    return normalized


def generate_address_quality_report(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Resume cobertura, método, confianza y revisiones requeridas."""

    summary = (
        dataframe.groupby(
            [
                "DIRECCION NORMALIZACION METODO",
                "DIRECCION NORMALIZACION CONFIANZA",
                "DIRECCION REQUIERE REVISION",
            ],
            dropna=False,
            as_index=False,
        )
        .size()
        .rename(columns={"size": "CANTIDAD_FILAS"})
    )

    summary["PORCENTAJE_FILAS"] = (
        summary["CANTIDAD_FILAS"]
        .div(len(dataframe) if len(dataframe) else 1)
        .mul(100)
        .round(2)
    )

    return summary
