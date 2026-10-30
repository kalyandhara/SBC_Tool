# Sector rotation around planetary events (phase 1)

Pre-registration: `docs/research/sector_rotation_preregistration_2026-10-29.md` (commit 1f1911c)

**Confirmatory outcome: empty list. No pre-registered edge.** Every table below is descriptive, not graded.

Forecast: each event carries "No call". This is a historical pattern, not trading advice.

Breadth: not computed (needs constituent data, phase 2).

Out-of-sample era from 2021-10-01: 1254 sessions.

## Coverage

| Sector | First | Last | Sessions | Note |
|---|---|---|---|---|
| CNXBANK | 2007-09-17 | 2026-10-29 | 4705 |  |
| CNXFIN | 2011-09-07 | 2026-10-29 | 3712 |  |
| CNXIT | 2007-09-17 | 2026-10-29 | 4705 |  |
| CNXPHARMA | 2011-01-31 | 2026-10-29 | 3877 |  |
| CNXAUTO | 2011-07-12 | 2026-10-29 | 3751 |  |
| CNXFMCG | 2011-01-31 | 2026-10-29 | 3862 |  |
| CNXMETAL | 2011-07-12 | 2026-10-29 | 3751 |  |
| CNXENERGY | 2011-01-31 | 2026-10-29 | 3863 |  |
| CNXREALTY | 2010-07-19 | 2026-10-29 | 3998 |  |
| CNXPSUBANK | 2011-01-31 | 2026-10-29 | 3863 |  |
| CNXINFRA | 2010-07-19 | 2026-10-29 | 3998 |  |
| CNXCONSUM | 2011-07-12 | 2026-10-29 | 3749 |  |
| CNXMEDIA | None | None | 0 | short history |
| CNXHEALTH | None | None | 0 | short history |
| CNXOILGAS | None | None | 0 | short history |

## Event counts

| Event | Raw | Clusters |
|---|---|---|
| JUPITER_INGRESS | 32 | 30 |
| LUNAR_ECLIPSE | 45 | 41 |
| MERCURY_RETROGRADE_START | 63 | 61 |
| SATURN_INGRESS | 15 | 14 |
| SOLAR_ECLIPSE | 44 | 41 |

## Rotation labels (descriptive, not graded)

- JUPITER_INGRESS, T+5: 32 occurrences, labels {'insufficient': 8, 'Risk-On': 14, 'Mixed': 7, 'Defensive': 3}
- JUPITER_INGRESS, T+10: 32 occurrences, labels {'insufficient': 8, 'Mixed': 12, 'Risk-On': 12}
- JUPITER_INGRESS, T+20: 32 occurrences, labels {'insufficient': 8, 'Mixed': 9, 'Risk-On': 13, 'Defensive': 2}
- LUNAR_ECLIPSE, T+5: 45 occurrences, labels {'insufficient': 10, 'Risk-On': 17, 'Defensive': 5, 'Mixed': 13}
- LUNAR_ECLIPSE, T+10: 45 occurrences, labels {'insufficient': 10, 'Risk-On': 20, 'Mixed': 9, 'Defensive': 6}
- LUNAR_ECLIPSE, T+20: 45 occurrences, labels {'insufficient': 10, 'Risk-On': 16, 'Defensive': 3, 'Mixed': 16}
- MERCURY_RETROGRADE_START, T+5: 63 occurrences, labels {'insufficient': 15, 'Risk-On': 24, 'Defensive': 5, 'Mixed': 19}
- MERCURY_RETROGRADE_START, T+10: 63 occurrences, labels {'insufficient': 16, 'Risk-On': 18, 'Defensive': 9, 'Mixed': 20}
- MERCURY_RETROGRADE_START, T+20: 63 occurrences, labels {'insufficient': 15, 'Mixed': 17, 'Defensive': 11, 'Risk-On': 20}
- SATURN_INGRESS, T+5: 15 occurrences, labels {'insufficient': 3, 'Mixed': 5, 'Risk-On': 7}
- SATURN_INGRESS, T+10: 15 occurrences, labels {'insufficient': 3, 'Defensive': 3, 'Risk-On': 6, 'Mixed': 3}
- SATURN_INGRESS, T+20: 15 occurrences, labels {'insufficient': 3, 'Mixed': 5, 'Risk-On': 6, 'Defensive': 1}
- SOLAR_ECLIPSE, T+5: 44 occurrences, labels {'insufficient': 9, 'Risk-On': 21, 'Defensive': 5, 'Mixed': 9}
- SOLAR_ECLIPSE, T+10: 44 occurrences, labels {'insufficient': 9, 'Mixed': 17, 'Risk-On': 16, 'Defensive': 2}
- SOLAR_ECLIPSE, T+20: 44 occurrences, labels {'insufficient': 9, 'Risk-On': 15, 'Mixed': 18, 'Defensive': 2}

## Sector mean relative return (descriptive, not graded)

### JUPITER_INGRESS, T+5

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXPHARMA | 24 | 22 | +0.0079 | 0.42 | 0.54 |
| CNXAUTO | 23 | 21 | +0.0033 | 0.52 | 0.61 |
| CNXENERGY | 24 | 22 | +0.0028 | 0.46 | 0.50 |
| CNXMETAL | 23 | 21 | +0.0012 | 0.48 | 0.57 |
| CNXFMCG | 24 | 22 | +0.0010 | 0.29 | 0.42 |
| CNXINFRA | 26 | 24 | +0.0008 | 0.54 | 0.50 |
| CNXREALTY | 26 | 24 | +0.0008 | 0.50 | 0.42 |
| CNXBANK | 32 | 30 | +0.0005 | 0.50 | 0.44 |
| CNXCONSUM | 23 | 21 | +0.0003 | 0.39 | 0.48 |
| CNXFIN | 23 | 21 | -0.0002 | 0.30 | 0.48 |
| CNXPSUBANK | 24 | 22 | -0.0003 | 0.46 | 0.42 |
| CNXIT | 32 | 30 | -0.0068 | 0.59 | 0.50 |

### JUPITER_INGRESS, T+10

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXPHARMA | 24 | 22 | +0.0159 | 0.38 | 0.50 |
| CNXAUTO | 23 | 21 | +0.0091 | 0.52 | 0.61 |
| CNXENERGY | 24 | 22 | +0.0059 | 0.58 | 0.62 |
| CNXMETAL | 23 | 21 | +0.0052 | 0.52 | 0.57 |
| CNXINFRA | 26 | 24 | +0.0034 | 0.50 | 0.62 |
| CNXBANK | 32 | 30 | +0.0024 | 0.47 | 0.50 |
| CNXREALTY | 26 | 24 | +0.0022 | 0.58 | 0.50 |
| CNXFMCG | 24 | 22 | +0.0014 | 0.25 | 0.50 |
| CNXCONSUM | 23 | 21 | +0.0006 | 0.30 | 0.52 |
| CNXFIN | 23 | 21 | -0.0004 | 0.35 | 0.48 |
| CNXPSUBANK | 24 | 22 | -0.0017 | 0.38 | 0.46 |
| CNXIT | 32 | 30 | -0.0088 | 0.62 | 0.56 |

### JUPITER_INGRESS, T+20

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXPHARMA | 24 | 22 | +0.0132 | 0.50 | 0.58 |
| CNXAUTO | 23 | 21 | +0.0095 | 0.57 | 0.65 |
| CNXENERGY | 24 | 22 | +0.0067 | 0.38 | 0.54 |
| CNXREALTY | 26 | 24 | +0.0013 | 0.54 | 0.46 |
| CNXBANK | 32 | 30 | +0.0011 | 0.50 | 0.50 |
| CNXINFRA | 26 | 24 | +0.0002 | 0.50 | 0.54 |
| CNXFIN | 23 | 21 | -0.0001 | 0.35 | 0.43 |
| CNXPSUBANK | 24 | 22 | -0.0010 | 0.50 | 0.50 |
| CNXMETAL | 23 | 21 | -0.0016 | 0.52 | 0.43 |
| CNXIT | 32 | 30 | -0.0024 | 0.56 | 0.50 |
| CNXCONSUM | 23 | 21 | -0.0054 | 0.30 | 0.43 |
| CNXFMCG | 24 | 22 | -0.0112 | 0.25 | 0.33 |

### LUNAR_ECLIPSE, T+5

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXENERGY | 35 | 33 | +0.0087 | 0.57 | 0.60 |
| CNXMETAL | 34 | 32 | +0.0047 | 0.50 | 0.59 |
| CNXFMCG | 35 | 33 | +0.0035 | 0.43 | 0.51 |
| CNXINFRA | 36 | 34 | +0.0034 | 0.50 | 0.64 |
| CNXCONSUM | 34 | 32 | +0.0015 | 0.38 | 0.50 |
| CNXPHARMA | 35 | 33 | +0.0014 | 0.40 | 0.49 |
| CNXPSUBANK | 35 | 33 | +0.0003 | 0.46 | 0.49 |
| CNXBANK | 45 | 41 | -0.0030 | 0.49 | 0.47 |
| CNXFIN | 34 | 32 | -0.0036 | 0.29 | 0.47 |
| CNXIT | 45 | 41 | -0.0037 | 0.53 | 0.49 |
| CNXAUTO | 34 | 32 | -0.0051 | 0.35 | 0.50 |
| CNXREALTY | 36 | 34 | -0.0051 | 0.44 | 0.44 |

### LUNAR_ECLIPSE, T+10

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXENERGY | 35 | 33 | +0.0084 | 0.51 | 0.60 |
| CNXMETAL | 34 | 32 | +0.0071 | 0.53 | 0.53 |
| CNXPSUBANK | 35 | 33 | +0.0026 | 0.46 | 0.51 |
| CNXCONSUM | 34 | 32 | +0.0025 | 0.41 | 0.59 |
| CNXFMCG | 35 | 33 | +0.0014 | 0.43 | 0.51 |
| CNXFIN | 34 | 32 | +0.0006 | 0.35 | 0.50 |
| CNXINFRA | 36 | 34 | +0.0003 | 0.31 | 0.56 |
| CNXIT | 45 | 41 | -0.0002 | 0.58 | 0.51 |
| CNXBANK | 45 | 41 | -0.0010 | 0.51 | 0.51 |
| CNXPHARMA | 35 | 33 | -0.0024 | 0.46 | 0.57 |
| CNXAUTO | 34 | 32 | -0.0046 | 0.38 | 0.50 |
| CNXREALTY | 36 | 34 | -0.0082 | 0.42 | 0.47 |

### LUNAR_ECLIPSE, T+20

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXMETAL | 34 | 32 | +0.0112 | 0.65 | 0.65 |
| CNXENERGY | 35 | 33 | +0.0078 | 0.51 | 0.57 |
| CNXCONSUM | 34 | 32 | +0.0026 | 0.38 | 0.59 |
| CNXIT | 45 | 41 | +0.0001 | 0.58 | 0.53 |
| CNXPHARMA | 35 | 33 | -0.0002 | 0.37 | 0.43 |
| CNXFIN | 34 | 32 | -0.0007 | 0.26 | 0.47 |
| CNXFMCG | 35 | 33 | -0.0008 | 0.46 | 0.46 |
| CNXINFRA | 36 | 34 | -0.0008 | 0.36 | 0.53 |
| CNXREALTY | 36 | 34 | -0.0017 | 0.44 | 0.44 |
| CNXPSUBANK | 35 | 33 | -0.0020 | 0.46 | 0.46 |
| CNXAUTO | 34 | 32 | -0.0041 | 0.35 | 0.38 |
| CNXBANK | 45 | 41 | -0.0047 | 0.51 | 0.44 |

### MERCURY_RETROGRADE_START, T+5

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXPHARMA | 49 | 49 | +0.0034 | 0.47 | 0.59 |
| CNXFIN | 46 | 46 | +0.0025 | 0.41 | 0.52 |
| CNXREALTY | 50 | 50 | +0.0020 | 0.48 | 0.52 |
| CNXENERGY | 48 | 48 | +0.0016 | 0.35 | 0.42 |
| CNXFMCG | 48 | 48 | +0.0014 | 0.48 | 0.52 |
| CNXBANK | 62 | 60 | +0.0012 | 0.58 | 0.52 |
| CNXAUTO | 47 | 47 | +0.0010 | 0.47 | 0.55 |
| CNXCONSUM | 47 | 47 | +0.0003 | 0.36 | 0.53 |
| CNXPSUBANK | 48 | 48 | -0.0001 | 0.44 | 0.48 |
| CNXINFRA | 50 | 50 | -0.0017 | 0.34 | 0.46 |
| CNXIT | 62 | 60 | -0.0040 | 0.55 | 0.45 |
| CNXMETAL | 47 | 47 | -0.0040 | 0.43 | 0.47 |

### MERCURY_RETROGRADE_START, T+10

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXFMCG | 47 | 47 | +0.0058 | 0.49 | 0.60 |
| CNXBANK | 62 | 60 | +0.0042 | 0.58 | 0.53 |
| CNXFIN | 45 | 45 | +0.0029 | 0.49 | 0.51 |
| CNXCONSUM | 46 | 46 | +0.0027 | 0.46 | 0.63 |
| CNXENERGY | 47 | 47 | +0.0026 | 0.36 | 0.47 |
| CNXPHARMA | 49 | 49 | +0.0018 | 0.51 | 0.53 |
| CNXAUTO | 46 | 46 | +0.0004 | 0.48 | 0.50 |
| CNXREALTY | 49 | 49 | -0.0002 | 0.49 | 0.53 |
| CNXINFRA | 49 | 49 | -0.0024 | 0.31 | 0.45 |
| CNXIT | 62 | 60 | -0.0047 | 0.58 | 0.50 |
| CNXPSUBANK | 47 | 47 | -0.0068 | 0.30 | 0.34 |
| CNXMETAL | 46 | 46 | -0.0122 | 0.35 | 0.37 |

### MERCURY_RETROGRADE_START, T+20

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXFMCG | 48 | 48 | +0.0097 | 0.50 | 0.62 |
| CNXPHARMA | 49 | 49 | +0.0061 | 0.53 | 0.57 |
| CNXAUTO | 47 | 47 | +0.0042 | 0.49 | 0.60 |
| CNXCONSUM | 47 | 47 | +0.0029 | 0.47 | 0.60 |
| CNXFIN | 46 | 46 | +0.0027 | 0.43 | 0.46 |
| CNXBANK | 62 | 60 | +0.0014 | 0.52 | 0.45 |
| CNXREALTY | 50 | 50 | -0.0023 | 0.50 | 0.52 |
| CNXENERGY | 48 | 48 | -0.0024 | 0.35 | 0.40 |
| CNXIT | 62 | 60 | -0.0035 | 0.58 | 0.52 |
| CNXINFRA | 50 | 50 | -0.0044 | 0.32 | 0.46 |
| CNXMETAL | 47 | 47 | -0.0116 | 0.36 | 0.40 |
| CNXPSUBANK | 48 | 48 | -0.0123 | 0.31 | 0.35 |

### SATURN_INGRESS, T+5

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXFMCG | 12 | 12 | +0.0121 | 0.50 | 0.75 |
| CNXBANK | 15 | 14 | +0.0091 | 0.67 | 0.67 |
| CNXFIN | 12 | 12 | +0.0091 | 0.58 | 0.67 |
| CNXPHARMA | 12 | 12 | +0.0089 | 0.50 | 0.67 |
| CNXREALTY | 12 | 12 | +0.0059 | 0.58 | 0.50 |
| CNXCONSUM | 12 | 12 | +0.0036 | 0.42 | 0.67 |
| CNXAUTO | 12 | 12 | -0.0040 | 0.33 | 0.50 |
| CNXPSUBANK | 12 | 12 | -0.0047 | 0.42 | 0.50 |
| CNXINFRA | 12 | 12 | -0.0086 | 0.17 | 0.33 |
| CNXENERGY | 12 | 12 | -0.0113 | 0.17 | 0.17 |
| CNXIT | 15 | 14 | -0.0129 | 0.60 | 0.47 |
| CNXMETAL | 12 | 12 | -0.0183 | 0.25 | 0.25 |

### SATURN_INGRESS, T+10

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXFMCG | 12 | 12 | +0.0186 | 0.67 | 0.83 |
| CNXBANK | 15 | 14 | +0.0112 | 0.67 | 0.73 |
| CNXCONSUM | 12 | 12 | +0.0098 | 0.75 | 0.83 |
| CNXFIN | 12 | 12 | +0.0079 | 0.50 | 0.67 |
| CNXREALTY | 12 | 12 | +0.0020 | 0.42 | 0.50 |
| CNXPHARMA | 12 | 12 | +0.0015 | 0.42 | 0.58 |
| CNXAUTO | 12 | 12 | -0.0001 | 0.33 | 0.50 |
| CNXINFRA | 12 | 12 | -0.0081 | 0.08 | 0.17 |
| CNXPSUBANK | 12 | 12 | -0.0081 | 0.50 | 0.50 |
| CNXIT | 15 | 14 | -0.0088 | 0.53 | 0.67 |
| CNXENERGY | 12 | 12 | -0.0233 | 0.17 | 0.08 |
| CNXMETAL | 12 | 12 | -0.0258 | 0.17 | 0.17 |

### SATURN_INGRESS, T+20

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXFIN | 12 | 12 | +0.0119 | 0.75 | 0.83 |
| CNXBANK | 15 | 14 | +0.0106 | 0.80 | 0.53 |
| CNXFMCG | 12 | 12 | +0.0091 | 0.50 | 0.67 |
| CNXCONSUM | 12 | 12 | +0.0041 | 0.58 | 0.50 |
| CNXPHARMA | 12 | 12 | -0.0055 | 0.33 | 0.42 |
| CNXAUTO | 12 | 12 | -0.0081 | 0.33 | 0.50 |
| CNXIT | 15 | 14 | -0.0130 | 0.67 | 0.60 |
| CNXREALTY | 12 | 12 | -0.0132 | 0.42 | 0.50 |
| CNXPSUBANK | 12 | 12 | -0.0136 | 0.25 | 0.33 |
| CNXINFRA | 12 | 12 | -0.0219 | 0.08 | 0.25 |
| CNXENERGY | 12 | 12 | -0.0297 | 0.25 | 0.25 |
| CNXMETAL | 12 | 12 | -0.0474 | 0.17 | 0.17 |

### SOLAR_ECLIPSE, T+5

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXPHARMA | 35 | 33 | +0.0045 | 0.46 | 0.51 |
| CNXBANK | 44 | 41 | +0.0031 | 0.61 | 0.68 |
| CNXFMCG | 35 | 33 | +0.0013 | 0.54 | 0.54 |
| CNXFIN | 33 | 32 | +0.0012 | 0.45 | 0.61 |
| CNXPSUBANK | 35 | 33 | +0.0002 | 0.57 | 0.51 |
| CNXENERGY | 35 | 33 | -0.0019 | 0.29 | 0.29 |
| CNXCONSUM | 33 | 32 | -0.0024 | 0.36 | 0.42 |
| CNXINFRA | 36 | 34 | -0.0035 | 0.33 | 0.44 |
| CNXAUTO | 33 | 32 | -0.0036 | 0.33 | 0.48 |
| CNXIT | 44 | 41 | -0.0046 | 0.55 | 0.50 |
| CNXREALTY | 36 | 34 | -0.0047 | 0.44 | 0.44 |
| CNXMETAL | 33 | 32 | -0.0082 | 0.39 | 0.45 |

### SOLAR_ECLIPSE, T+10

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXBANK | 44 | 41 | +0.0033 | 0.55 | 0.57 |
| CNXFIN | 33 | 32 | +0.0024 | 0.58 | 0.55 |
| CNXFMCG | 35 | 33 | +0.0023 | 0.54 | 0.54 |
| CNXPSUBANK | 35 | 33 | +0.0013 | 0.40 | 0.49 |
| CNXIT | 44 | 41 | +0.0009 | 0.64 | 0.55 |
| CNXPHARMA | 35 | 33 | +0.0005 | 0.46 | 0.49 |
| CNXREALTY | 36 | 34 | +0.0004 | 0.47 | 0.50 |
| CNXCONSUM | 33 | 32 | -0.0034 | 0.39 | 0.39 |
| CNXENERGY | 35 | 33 | -0.0041 | 0.37 | 0.43 |
| CNXAUTO | 33 | 32 | -0.0066 | 0.21 | 0.33 |
| CNXINFRA | 36 | 34 | -0.0070 | 0.31 | 0.36 |
| CNXMETAL | 33 | 32 | -0.0088 | 0.42 | 0.45 |

### SOLAR_ECLIPSE, T+20

| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |
|---|---|---|---|---|---|
| CNXFIN | 33 | 32 | +0.0023 | 0.48 | 0.55 |
| CNXREALTY | 36 | 34 | +0.0022 | 0.44 | 0.44 |
| CNXIT | 44 | 41 | +0.0018 | 0.59 | 0.52 |
| CNXFMCG | 35 | 33 | +0.0015 | 0.54 | 0.63 |
| CNXPSUBANK | 35 | 33 | -0.0011 | 0.37 | 0.40 |
| CNXBANK | 44 | 41 | -0.0021 | 0.52 | 0.57 |
| CNXPHARMA | 35 | 33 | -0.0024 | 0.43 | 0.40 |
| CNXMETAL | 33 | 32 | -0.0030 | 0.45 | 0.52 |
| CNXCONSUM | 33 | 32 | -0.0041 | 0.33 | 0.45 |
| CNXENERGY | 35 | 33 | -0.0044 | 0.37 | 0.37 |
| CNXAUTO | 33 | 32 | -0.0046 | 0.45 | 0.45 |
| CNXINFRA | 36 | 34 | -0.0057 | 0.36 | 0.47 |

## Inputs

Price rows SHA-256: `7961eb343b9cb8b9cdb26f815204ea4f2221135d57e94732dce80d9bea1f1ed1`

Last session per series:

- NIFTY: 2026-10-29
- CNXBANK: 2026-10-29
- CNXFIN: 2026-10-29
- CNXIT: 2026-10-29
- CNXPHARMA: 2026-10-29
- CNXAUTO: 2026-10-29
- CNXFMCG: 2026-10-29
- CNXMETAL: 2026-10-29
- CNXENERGY: 2026-10-29
- CNXREALTY: 2026-10-29
- CNXPSUBANK: 2026-10-29
- CNXINFRA: 2026-10-29
- CNXCONSUM: 2026-10-29
- CNXMEDIA: None
- CNXHEALTH: None
- CNXOILGAS: None
