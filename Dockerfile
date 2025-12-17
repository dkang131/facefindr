FROM python:3.13-bookworm AS builder

RUN apt-get update && apt-get install --no-install-recommends -y \
        build-essential && \
    apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app

COPY ./pyproject.toml ./uv.lock* ./

RUN uv sync \
    --no-dev \
    --no-cache \
    --frozen \
    --all-extras

FROM python:3.13-slim-bookworm AS production

RUN apt-get update && apt-get install --no-install-recommends -y \
        libgl1-mesa-glx \
        libglib2.0-0 \
        && apt-get clean && rm -rf /var/lib/apt/lists/* \
        && rm -rf /var/cache/apt/*

WORKDIR /app

# Copy venv form builder stage 
COPY --from=builder /app/.venv /app/.venv

COPY ./alembic ./alembic
COPY ./auth ./auth
COPY ./cms ./cms
COPY ./download ./download
COPY ./services ./services
COPY ./static ./static
COPY ./utils ./utils
COPY ./alembic.ini .
COPY ./config.py .
COPY ./database.py .
COPY ./extensions.py .
COPY ./main.py .
COPY ./models.py .
COPY ./reset_password.py .

ENV PATH="/app/.venv/bin:$PATH"

# ENV FLASK_APP=main.py

EXPOSE 7219

CMD [ "python", "main.py" ]
