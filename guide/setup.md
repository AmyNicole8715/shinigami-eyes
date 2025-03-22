# Setup Guide for Enhanced Shinigami Eyes

This guide walks through setting up the enhanced Shinigami Eyes extension with ML-based verification.

## Prerequisites

- Ubuntu 24.04 or compatible Linux distribution
- Ollama installed with Gemma 3:4b model
- Python 3.10+
- Basic familiarity with terminal commands

## Installation Steps

### 1. Set Up Python Environment

```bash
# Install Python dependencies
sudo apt update
sudo apt install python3-pip python3-venv

# Create a virtual environment
mkdir -p ~/shinigami_ml
cd ~/shinigami_ml
python3 -m venv env
source env/bin/activate

# Install necessary packages
pip install torch torchvision torchaudio
pip install pandas numpy scikit-learn flask
pip install spacy
python -m spacy download en_core_web_md
pip install requests beautifulsoup4 warcio
```

### 2. Ollama Setup

Ensure Ollama is running and has Gemma 3:4b model:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# Pull Gemma 3:4b if not already available
ollama pull gemma:4b
```

### 3. Clone the Repository

```bash
# Navigate to your desired location
cd ~/Coding/Personal_Projects/Extensions/shini/

# Make sure you're in the right directory
git pull

# Install development dependencies
cd shinigami-eyes
npm install
```

### 4. Start the ML Service

```bash
# Navigate to the ML service directory
cd ~/shinigami_ml

# Activate the virtual environment if not already active
source env/bin/activate

# Start the service
python ~/Coding/Personal_Projects/Extensions/shini/shinigami-eyes/ml_service/app.py
```

The service will run on http://localhost:5000 by default.

### 5. Load the Extension in Developer Mode

For Chrome:
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `shinigami-eyes/extension` directory

For Firefox:
1. Open Firefox and go to `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on..."
3. Select any file in the `shinigami-eyes/extension` directory

## Training Your Own Model

See the [training.md](training.md) guide for detailed instructions on training the model with your own dataset.
