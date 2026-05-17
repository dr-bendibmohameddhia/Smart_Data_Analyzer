<<<<<<< HEAD
# Smart Data Analyzer

> Instant statistical profiles, interactive visualisations, and data-cleaning tools for any CSV, Excel, or Parquet file — no code required.

---

## Description

Most data-exploration workflows begin the same way: someone drops a spreadsheet on your desk, asks *"what's in here?"*, and expects an answer by end of day.  Smart Data Analyzer was built to compress that turnaround from hours to minutes.

Upload a file, and the tool automatically profiles every column, builds a correlation matrix, surfaces outliers, and gives you a cleaning pipeline you can apply and download — all through a browser UI that runs locally or deploys to any cloud platform that supports Streamlit.

The target audience is analysts, product managers, and engineers who need quick answers from data without writing pandas boilerplate each time.

---

## Features

- **Automatic column profiling** — mean, median, standard deviation, skewness, kurtosis, IQR, and outlier count for every numeric column; top-N value frequencies for categoricals.
- **Missing-value audit** — colour-coded bar chart showing which columns need attention and by how much.
- **Interactive distributions** — histogram with KDE overlay, box plots, and violin plots, all filterable by categorical group.
- **Scatter plots with trendlines** — OLS trendline, optional colour/size encoding, automatic down-sampling for large datasets.
- **Correlation heat-map** — full Pearson matrix with automatic flagging of highly correlated column pairs.
- **Pair plot** — scatter matrix for exploring up to six columns simultaneously.
- **Time-series view** — line chart with configurable resampling (daily / weekly / monthly / quarterly).
- **Outlier detection** — IQR (Tukey fence) and Z-score methods; export flagged rows as CSV.
- **Guided cleaning pipeline** — duplicate removal, configurable missing-value imputation, near-empty column dropping; download the cleaned dataset directly.
- **Multi-format support** — CSV, TSV, Excel (`.xlsx` / `.xls`), and Parquet files up to 200 MB.

---

## Tech Stack

| Layer | Library | Version |
|---|---|---|
| UI framework | Streamlit | 1.35 |
| Data manipulation | pandas | 2.2 |
| Numerical computing | NumPy | 1.26 |
| Interactive charts | Plotly | 5.22 |
| Statistical functions | SciPy | 1.13 |
| ML utilities | scikit-learn | 1.5 |
| Excel I/O | openpyxl / xlrd | 3.1 / 2.0 |
| Columnar I/O | pyarrow | 16 |

---

## Project Structure

```
Smart_Data_Analyzer/
├── .gitignore
├── README.md
├── requirements.txt
└── src/
    ├── __init__.py
    ├── main.py                      # Entry point, navigation, global CSS
    ├── components/
    │   ├── __init__.py
    │   ├── data_loader.py           # File ingestion & validation
    │   ├── data_processing.py       # Statistical profiling & cleaning
    │   ├── data_visualization.py    # Plotly chart builders
    │   └── utils.py                 # Shared helpers
    └── pages/
        ├── __init__.py
        ├── home.py                  # Upload & preview
        ├── analyze_data.py          # Full analysis (5 tabs)
        └── about.py                 # Project info & roadmap
```

The architecture follows a strict layered separation:

- **`pages/`** handles Streamlit rendering, user input, and session state.
- **`components/`** contains pure Python logic with no Streamlit dependencies — making it unit-testable and reusable outside the UI context.
- **`main.py`** owns global configuration, navigation, and page dispatch.

---

## Installation

### Prerequisites

- Python 3.11 or higher
- `pip` package manager (bundled with Python)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/smart-data-analyzer.git
cd smart-data-analyzer

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv

# On macOS / Linux:
source .venv/bin/activate

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

---

## How to Run

```
python -m streamlit run src/main.py
```

Streamlit will print a local URL (typically `http://localhost:8501`).  Open it in your browser.

### Optional environment variables

Create a `.env` file in the project root to override defaults:

```dotenv
# Maximum upload size in megabytes (default: 200)
MAX_FILE_SIZE_MB=500

# Streamlit server port (default: 8501)
STREAMLIT_SERVER_PORT=8080
```

---

## Deployment

### Streamlit Community Cloud (free tier)

1. Push the repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and click **New app**.
3. Set the main file path to `src/main.py`.
4. Click **Deploy**.

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "src/main.py", "--server.headless=true"]
```

```bash
docker build -t smart-data-analyzer .
docker run -p 8501:8501 smart-data-analyzer
```

---

## Screenshots

_Replace the placeholder paths below with actual screenshots after your first run._

**Home — file upload and preview**
```
![Home page](docs/screenshots/home.png)
```

**Overview tab — KPIs, type breakdown, missing-value chart**
```
![Overview tab](docs/screenshots/overview.png)
```

**Distributions tab — histogram with KDE overlay**
```
![Distributions tab](docs/screenshots/distributions.png)
```

**Relationships tab — correlation heat-map**
```
![Correlation heatmap](docs/screenshots/correlation.png)
```

**Outliers tab — strip chart with highlighted anomalies**
```
![Outliers tab](docs/screenshots/outliers.png)
```

---

## Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run all tests with coverage report
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Future Improvements

- **AI-generated narrative** — plain-English summary of the most interesting patterns, powered by an LLM API.
- **Geospatial visualisation** — detect latitude/longitude columns and render a Mapbox choropleth.
- **PDF export** — one-click professional report with embedded charts.
- **Database connectors** — query PostgreSQL, BigQuery, or Snowflake directly without CSV export.
- **Scheduled dataset refreshes** — periodically reload from a URL and push a Slack/email digest.
- **Column-level lineage** — track all cleaning operations and emit a reproducible pandas script.
- **Multi-file comparison** — upload two datasets and diff them column by column.
- **Anomaly timeline** — for time-series columns, highlight date ranges with statistically unusual values.

---

## Contributing

Contributions are welcome.  Please follow the standard fork → branch → pull-request workflow:

1. Fork the repository and create a feature branch (`git checkout -b feat/my-feature`).
2. Write your code and add tests where applicable.
3. Format with `black` and lint with `ruff` before committing.
4. Open a pull request with a clear description of the change and its motivation.

For significant changes, open an issue first to discuss scope and approach.

---

## License

This project is licensed under the **MIT License**.  See [`LICENSE`](LICENSE) for details.

## Screenshots

### Home Page
![Home Screenshot](assets/0.png)

### Analyze Page
![Analyze Screenshot](assets/1.png)

### Export Page
![Export Screenshot](assets/3.png)
=======
# Smart_Data_Analyzer
>>>>>>> 4489fbead3bc416ec26ae9f8e9fda6c869a9c1a7
