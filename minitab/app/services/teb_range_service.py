"""Compute a TEB range column (max abs TEB across selected temperatures)."""

import re

import pandas as pd

from app.utils.logger import logger

# Matches a per-temperature TEB column, e.g. "TEB @ 0C", "TEB @ -40C".
# The optional suffix handles duplicate headers normalized by pandas, such as
# "TEB @ 25C.1" and "TEB @ 25C.2".
# Deliberately excludes:
#   * "TEB AZ @ 25C"      (different metric -> "TEB @ " prefix won't match)
#   * other columns with a different metric prefix
_TEB_COL_RE = re.compile(
    r"^TEB\s*@\s*(-?\d+(?:\.\d+)?)\s*C(?:\.\d+)?$",
    re.IGNORECASE,
)
_TOL = 1e-9


class TEBRangeService:
    @staticmethod
    def _temperature_columns(df):
        """Map temperature value -> all matching column positions."""
        mapping = {}
        for position, col in enumerate(df.columns):
            m = _TEB_COL_RE.match(str(col).strip())
            if m:
                mapping.setdefault(float(m.group(1)), []).append(position)
        return mapping

    @staticmethod
    def calculate_range(df, temps, column_name):
        """Add ``column_name`` = max(|TEB @ t|) over the given temperatures.

        Temperatures are matched *numerically* against the ``TEB @ <n>C`` columns,
        so 0 / 0.0 / "  0 " all resolve to the ``TEB @ 0C`` column. Temperatures
        with no matching column are skipped with a warning rather than raising.
        """
        available = TEBRangeService._temperature_columns(df)

        present, missing = [], []
        for t in temps:
            try:
                tf = float(t)
            except (TypeError, ValueError):
                missing.append(t)
                continue
            matches = next(
                (positions for val, positions in available.items()
                 if abs(val - tf) < _TOL),
                None,
            )
            if matches:
                present.extend(matches)
            else:
                missing.append(t)

        if missing:
            logger.warning(
                "TEB range: no column matched temperatures {}. Available: {}",
                missing, sorted(available.keys()),
            )

        if not present:
            logger.warning(
                "TEB range: no matching TEB columns found; '{}' set to NaN.",
                column_name,
            )
            df[column_name] = pd.NA
            return df

        selected_columns = df.iloc[:, present]
        logger.info("TEB range from columns: {}", list(selected_columns.columns))
        df[column_name] = selected_columns.abs().max(axis=1)
        return df
