"""KP Intraday Configuration Layer.

Centralized configuration for weights, thresholds, and rule parameters.
All values can be overridden via environment variables or config file.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class KPConfig:
    """Complete KP Intraday configuration."""

    # Rule weights for signal scoring
    weights: Dict[str, float] = None

    # Signal classification thresholds
    thresholds: Dict[str, float] = None

    # Hora quality base mappings
    hora_base_quality: Dict[str, str] = None

    # Planet nature classifications
    planet_nature: Dict[str, str] = None

    # Trading rules
    max_tier1_trades: int = 3
    counter_regime_size_reduction: float = 0.5
    confirmation_candles: int = 5
    confirmation_points: int = 15
    timing_tolerance_minutes: int = 5

    # Bank Nifty calibration
    banknifty_timing_tolerance: int = 5
    banknifty_response_multiplier: float = 1.3
    banknifty_rahu_sl_multiplier: float = 2.0

    # Report branding
    brand: str = "Astro Quant Research Initiative | Trading Bramha Consulting"
    analyst: str = "KP Intraday Engine v1.0"

    # Output settings
    default_format: str = "html"
    include_css: bool = True

    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                'hora_weight': 0.3,
                'house_set_weight': 0.4,
                'moon_sub_weight': 0.2,
                'asc_sub_weight': 0.1,
            }
        if self.thresholds is None:
            self.thresholds = {
                'tier1_min_score': 5.0,
                'tier2_min_score': 3.0,
                'pure_set_min_score': 7.0,
                'regime_shift_min_strength': 1.5,
            }
        if self.hora_base_quality is None:
            self.hora_base_quality = {
                'Sun': 'Aggressive', 'Moon': 'Fruitful', 'Mars': 'Aggressive',
                'Mercury': 'Neutral', 'Jupiter': 'Fruitful', 'Venus': 'Fruitful',
                'Saturn': 'Sluggish', 'Rahu': 'Volatile', 'Ketu': 'Volatile',
            }
        if self.planet_nature is None:
            self.planet_nature = {
                'Sun': 'malefic', 'Moon': 'benefic', 'Mars': 'malefic',
                'Mercury': 'neutral', 'Jupiter': 'benefic', 'Venus': 'benefic',
                'Saturn': 'malefic', 'Rahu': 'malefic', 'Ketu': 'malefic'
            }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KPConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def override_from_env(self):
        """Override config from environment variables."""
        env_mappings = {
            'KP_HORA_WEIGHT': ('weights', 'hora_weight', float),
            'KP_HOUSE_SET_WEIGHT': ('weights', 'house_set_weight', float),
            'KP_MOON_SUB_WEIGHT': ('weights', 'moon_sub_weight', float),
            'KP_ASC_SUB_WEIGHT': ('weights', 'asc_sub_weight', float),
            'KP_TIER1_THRESHOLD': ('thresholds', 'tier1_min_score', float),
            'KP_TIER2_THRESHOLD': ('thresholds', 'tier2_min_score', float),
            'KP_PURE_SET_THRESHOLD': ('thresholds', 'pure_set_min_score', float),
            'KP_REGIME_THRESHOLD': ('thresholds', 'regime_shift_min_strength', float),
            'KP_MAX_TRADES': ('max_tier1_trades', None, int),
            'KP_BRAND': ('brand', None, str),
        }

        for env_var, (section, key, caster) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    casted = caster(value)
                    if section and key:
                        getattr(self, section)[key] = casted
                    elif key is None:
                        setattr(self, section, casted)
                except ValueError:
                    pass


DEFAULT_CONFIG = KPConfig()

CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "kp_intraday.json"


def load_config(config_path: Optional[Path] = None) -> KPConfig:
    """Load configuration from file, with environment overrides."""
    config = DEFAULT_CONFIG

    path = config_path or CONFIG_FILE
    if path.exists():
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            config = KPConfig.from_dict(data)
        except Exception:
            pass

    config.override_from_env()
    return config


def save_config(config: KPConfig, config_path: Optional[Path] = None):
    """Save configuration to file."""
    path = config_path or CONFIG_FILE
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(path, 'w') as f:
        json.dump(config.to_dict(), f, indent=2)


def get_config() -> KPConfig:
    """Get the active configuration (singleton pattern)."""
    if not hasattr(get_config, '_config'):
        get_config._config = load_config()
    return get_config._config


def reset_config():
    """Reset to default configuration."""
    get_config._config = DEFAULT_CONFIG


# Instrument-specific overrides
INSTRUMENT_OVERRIDES = {
    "NIFTY": {
        "timing_tolerance_minutes": 3,
        "response_multiplier": 1.0,
    },
    "BANK NIFTY": {
        "timing_tolerance_minutes": 5,
        "response_multiplier": 1.3,
    },
    "FINNIFTY": {
        "timing_tolerance_minutes": 5,
        "response_multiplier": 1.2,
    }
}


def get_instrument_config(instrument: str, base_config: KPConfig) -> Dict[str, Any]:
    """Get merged config for a specific instrument."""
    override = INSTRUMENT_OVERRIDES.get(instrument.upper(), {})
    return {**base_config.__dict__, **override}