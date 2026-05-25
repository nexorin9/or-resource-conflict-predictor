# Operating Room Resource Conflict Predictor

Predicts surgical duration fluctuations based on historical surgery data, proactively detects instrument/anesthesia/lead-surgeon conflicts, and outputs scheduling recommendations for department coordination.

## Features

- **Duration Prediction**: Predicts surgery duration based on historical data, with confidence intervals
- **Conflict Detection**: Instrument conflicts, anesthesia equipment conflicts, lead surgeon time conflicts
- **Scheduling Optimization**: Generates scheduling optimization recommendations based on conflict detection results
- **Multi-format Reports**: Supports text, CSV, and HTML format output
- **Visualization**: ASCII schedule with conflict highlighting

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Predict Surgery Duration

```bash
python -m src predict --surgery-type "Laparoscopic Cholecystectomy" --department "General Surgery" --surgeon "Dr. Zhang"
```

### Detect Conflicts

```bash
python -m src detect-conflicts --date 2024-01-15
```

### Generate Report

```bash
python -m src generate-report --format html --output report.html
```

## Project Structure

```
or-resource-conflict-predictor/
├── src/              # Source code
├── data/             # Data directory
├── templates/        # Report templates
├── models/           # Saved models
├── README.md
├── requirements.txt
└── .gitignore
```

## License

MIT License

---

## Support the Author

If you find this project helpful, feel free to buy me a coffee! ☕

![Buy Me a Coffee](buymeacoffee.png)

**Buy me a coffee (crypto)**

| Chain | Address |
|-------|---------|
| BTC | `bc1qc0f5tv577z7yt59tw8sqaq3tey98xehy32frzd` |
| ETH / USDT | `0x3b7b6c47491e4778157f0756102f134d05070704` |
| SOL | `6Xuk373zc6x6XWcAAuqvbWW92zabJdCmN3CSwpsVM6sd` |
