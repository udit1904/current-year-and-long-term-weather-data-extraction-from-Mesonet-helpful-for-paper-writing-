# mesonet-season-vs-baseline

Compare one growing season weather at a Kansas Mesonet station with the mean of earlier years.

The script downloads daily data from the [Kansas Mesonet](https://mesonet.k-state.edu) using the [ksmesopy](https://github.com/soilwater/ksmesopy) package. It computes FAO-56 Penman-Monteith reference ET (ETo) and returns season and monthly summaries you can use in a paper or report.

## What it does

1. Finds the Kansas Mesonet stations nearest to your field and picks one (or uses the one you name).
2. Reads the station's record length and only requests dates that exist.
3. Checks which variables the station serves and skips the missing ones.
4. Downloads daily data one year at a time, so one failed year does not stop the run.
5. Computes daily grass reference ET (ETo) with FAO-56 Penman-Monteith.
6. Sums or averages each variable over the growing season for every year.
7. Marks a year as complete only if at least 90% of its season days have temperature, precipitation and ETo.
8. Compares the target season with the mean of the complete earlier years.
9. Prints a monthly breakdown for the target season and the baseline.

## Outputs

| Output | Content |
|---|---|
| `mesonet_daily.csv` | Daily data for the season months of every year, with ETo |
| Per-year table | Mean, min and max air temperature, precipitation, ETo, data completeness |
| Season summary | Target year vs baseline mean, absolute and percent difference |
| Monthly table | Target year monthly temperature, precipitation and ETo next to the baseline |

The script also prints the baseline period in a form you can paste into a methods section, for example: `compared with the 2017–2025 mean (9 years)`.

## Variables used

| Mesonet name | Meaning | Unit |
|---|---|---|
| `TEMP2MAVG`, `TEMP2MMIN`, `TEMP2MMAX` | Air temperature at 2 m (mean, min, max) | °C |
| `PRECIP` | Precipitation, gauge 1 | mm |
| `SRAVG` | Solar radiation | W m⁻² |
| `WSPD2MAVG` | Wind speed at 2 m | m s⁻¹ |
| `RELHUM2MMIN`, `RELHUM2MMAX` | Relative humidity at 2 m (min, max) | % |
| `VPDEFAVG` | Vapor pressure deficit | kPa |

## Requirements

- Python 3.9 or newer
- `ksmesopy` (installs `numpy`, `pandas` and `matplotlib`)
- `ipython` (for `display`; already present in Colab and Jupyter)

## How to run

### Google Colab

1. Open a new notebook.
2. Paste each `# %%` block of `mesonet_season_vs_baseline.py` into its own cell.
3. Run STEP 0 once to install the package.
4. Edit STEP 1 and run STEP 1 and STEP 2.

### Local

```bash
git clone https://github.com/<your-username>/mesonet-season-vs-baseline.git
cd mesonet-season-vs-baseline
pip install -r requirements.txt
```

Open `mesonet_season_vs_baseline.py` in VS Code or Jupyter and run it cell by cell. Change `OUT_CSV` to a local path first. The default path `/content/` exists only in Colab.

## Inputs (STEP 1)

| Setting | Meaning | Example |
|---|---|---|
| `FARM_LAT`, `FARM_LON` | Field location in decimal degrees | `38.04`, `-101.04` |
| `STATION` | Mesonet station name. `None` picks the nearest one | `"Roth Tech Farm"` |
| `SEASON_YEAR` | Year to evaluate | `2026` |
| `SEASON` | First and last month of the season | `(5, 9)` for May to September |
| `BASE_YEARS` | Baseline years. `None` uses all complete years before `SEASON_YEAR` | `(2016, 2025)` |
| `OUT_CSV` | Path for the daily CSV | `/content/mesonet_daily.csv` |

## Method notes

- **ETo.** FAO-56 Penman-Monteith for a grass reference, computed by `ksmesopy.reference_et_penman_monteith`. Humidity comes from RHmin and RHmax when available, otherwise from VPD. Solar radiation is converted from W m⁻² inside the function.
- **Elevation.** Taken from the station metadata. If the metadata has no elevation column, the script uses 900 m. Check this for your station, because it affects the psychrometric constant.
- **Daily timestamps.** The Mesonet stores daily values at 00:00 of the next day. `ksmesopy` shifts them back, so each row is the observation date.
- **Completeness rule.** A season counts in the baseline only if temperature, precipitation and ETo each cover at least 90% of its days.
- **Short records.** If the station has fewer than 5 complete earlier years, the script warns you. Call this a short-term comparison, not a long-term or climate normal.
- **Monthly sums.** Monthly precipitation and ETo totals treat missing days as zero. Check the missing-day count before you report monthly values.

## Limitations


## Data source

Kansas Mesonet, Kansas State University. https://mesonet.k-state.edu

## Author

Udit Debangshi, PhD student at KState


