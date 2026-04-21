# R 4.5.2 + Python 3.11 reproducibility image.
FROM rocker/r-ver:4.5.2

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip \
    build-essential libcurl4-openssl-dev libssl-dev libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

# R deps via renv
COPY renv.lock ./
COPY install_r_deps.R ./
RUN R -e "install.packages('renv', repos='https://cloud.r-project.org/'); renv::restore(prompt=FALSE)"

# Python deps
COPY pyproject.toml ./
RUN python3.11 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -e ".[dev]"
ENV PATH="/opt/venv/bin:${PATH}"

# Project code
COPY . .

# Default: run tests. Override with `docker run ... python analysis/01_run_methods.py` etc.
CMD ["python", "-m", "pytest", "-v"]
