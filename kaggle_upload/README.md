# Kaggle Upload Packages

This folder contains local Kaggle dataset packages for the project.

## Final Package

Use this package:

- `used-car-price-intelligence-trusted-modeling-datasets/`

Kaggle dataset path used by the notebooks:

```text
/kaggle/input/datasets/hrushikeshnettetla/used-car-price-trusted-modeling-datasets
```

Final dataset files inside that package:

| File | Rows | Role |
| --- | ---: | --- |
| `live_trusted_market_snapshot_3496.csv` | 3,496 | Current-market trusted benchmark |
| `external_true_value_historical_dataset_5614.csv` | 5,614 | Historical True Value benchmark |
| `combined_trusted_modeling_dataset_9110.csv` | 9,110 | Main combined modeling dataset |

## Git Policy

CSV files are intentionally ignored by Git. They stay available locally for Kaggle upload, but the GitHub repository should keep only code, notebooks, docs, config, and small metadata.

The final package README, manifest, and experiment registry explain the dataset structure and modeling lineage.

## Release Caution

The external True Value Kaggle source used during modeling is recorded in this
project as `CC0-1.0`. Live scraped CSVs should remain outside Git and should not
be redistributed publicly unless the relevant source terms permit it.
