"""Configuration for the PTS analyzer (transfer function + product spec inputs)."""

from dataclasses import MISSING, dataclass, fields


class ConfigError(ValueError):
    """Raised when user-supplied configuration values are invalid."""


ASIC_ELMOS = "ELMOS"
ASIC_3224 = "ASIC 3224 (counts / 2^24 * 100)"
ASIC_OPTIONS = (ASIC_ELMOS, ASIC_3224)


@dataclass
class PTSConfig:
    # Transfer function
    pressure_min: float
    pressure_max: float
    output_min: float
    output_max: float
    supply_voltage: float
    pressure_az: float

    # Product spec limits
    teb_limit: float
    offset_limit: float
    span_limit: float
    linearity_limit: float
    pressure_hyst: float
    temp_hyst: float
    accuracy: float

    # Descriptors
    sensor_type: str = "differential"
    pressure_unit: str = "inH2O"
    asic_type: str = ASIC_ELMOS

    def validate(self) -> None:
        """Sanity-check the values, raising ConfigError with a clear message."""
        if self.pressure_min >= self.pressure_max:
            raise ConfigError(
                "Pressure min must be less than pressure max "
                f"(got min={self.pressure_min}, max={self.pressure_max})."
            )
        if self.output_min >= self.output_max:
            raise ConfigError(
                "Output min must be less than output max "
                f"(got min={self.output_min}, max={self.output_max})."
            )
        if self.supply_voltage <= 0:
            raise ConfigError("Supply voltage must be greater than 0.")
        if not self.sensor_type.strip():
            raise ConfigError("Sensor type must not be empty.")
        if not self.pressure_unit.strip():
            raise ConfigError("Pressure unit must not be empty.")

    @classmethod
    def from_dict(cls, values: dict) -> "PTSConfig":
        """Build a PTSConfig from a dict of strings (e.g. UI form inputs).

        Numeric fields are parsed with a helpful error naming the offending
        field, instead of a bare ``could not convert string to float``.
        """
        text_fields = {"sensor_type", "pressure_unit", "asic_type"}
        kwargs = {}
        for f in fields(cls):
            if f.name not in values:
                # Missing field: fall back to the dataclass default if one exists.
                if f.default is not MISSING or f.default_factory is not MISSING:
                    continue
                raise ConfigError(f"Missing required value: '{f.name}'.")
            raw = values.get(f.name, "")
            if f.name in text_fields:
                kwargs[f.name] = str(raw).strip()
            else:
                label = f.name.replace("_", " ").title()
                try:
                    kwargs[f.name] = float(raw)
                except (TypeError, ValueError):
                    raise ConfigError(
                        f"'{label}' must be a number (got '{raw}')."
                    ) from None
        config = cls(**kwargs)
        config.validate()
        return config
