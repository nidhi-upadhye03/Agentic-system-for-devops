# Base image with Python and Node.js
FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=development

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build tools
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    # Python dependencies
    python3.12 \
    python3.12-dev \
    python3-pip \
    python3-venv \
    # Node.js and npm (latest LTS)
    curl \
    wget \
    gnupg2 \
    # PostgreSQL client
    postgresql-client \
    # Redis client
    redis-tools \
    # Git
    git \
    # Other utilities
    vim \
    nano \
    less \
    jq \
    htop \
    net-tools \
    iputils-ping \
    telnet \
    dnsutils \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install Python tools
RUN pip3 install --no-cache-dir --upgrade \
    pip \
    setuptools \
    wheel \
    virtualenv \
    pipenv \
    poetry \
    black \
    pylint \
    flake8 \
    mypy \
    pytest \
    pytest-cov \
    pytest-asyncio

# Install global Node.js tools
RUN npm install -g \
    npm@latest \
    yarn \
    pnpm \
    eslint \
    prettier \
    nodemon \
    pm2 \
    typescript \
    ts-node

# Create workspace directory
RUN mkdir -p /workspace
WORKDIR /workspace

# Create non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Switch to non-root user
USER $USERNAME

# Set shell
SHELL ["/bin/bash", "-c"]
