# Training Guide for Shinigami Eyes ML Model

This guide explains how to train a custom Gemma 3:4b model using Ollama for the enhanced Shinigami Eyes extension.

## Prerequisites

- Completed the steps in [setup.md](setup.md)
- Prepared dataset of transphobic and trans-friendly content
- At least 16GB RAM recommended (8GB minimum)

## Dataset Preparation

### 1. Create Training Dataset

Create a CSV file with the following structure:

```csv
text,label
"This is a transphobic statement...",2
"This is a trans-friendly statement...",0
"This requires more information to classify...",1
```

Labels:
- 0 = Trans-friendly content
- 1 = Requires more data (gray area)
- 2 = Transphobic content

Save this as `training_data.csv` in your `~/shinigami_ml/data/` directory.

### 2. Split the Dataset

```bash
# Navigate to your ML directory
cd ~/shinigami_ml
source env/bin/activate

# Run the dataset splitter
python ~/Coding/Personal_Projects/Extensions/shini/shinigami-eyes/ml_service/scripts/split_dataset.py
```

## Training Methods

### Option 1: Using Ollama (Recommended for Simplicity)

```bash
# Navigate to your ML directory
cd ~/shinigami_ml

# Create Modelfile for training
cat > Modelfile << EOF
FROM gemma:4b

# Define your fine-tuning parameters
PARAMETER temperature 0.2
PARAMETER top_p 0.8

# Include training context
SYSTEM """
You are an expert content analyzer specializing in identifying transphobic and trans-friendly content.
You will classify text on a scale:
0 = definitely trans-friendly content
1 = unclear or requires more context
2 = definitely transphobic content

Always respond with only the number: 0, 1, or 2.
"""
EOF

# Create your custom model
ollama create transphobia-detector -f Modelfile

# Test the model
ollama run transphobia-detector "Analyze this content for transphobia: [paste example here]"
```

### Option 2: Using PyTorch for More Control

```bash
# Navigate to your ML directory
cd ~/shinigami_ml
source env/bin/activate

# Run the training script
python ~/Coding/Personal_Projects/Extensions/shini/shinigami-eyes/ml_service/scripts/train_model.py
```

The training process will take several hours depending on your hardware. The script will save checkpoints periodically.

## Evaluating Your Model

```bash
# Evaluate the model on test set
python ~/Coding/Personal_Projects/Extensions/shini/shinigami-eyes/ml_service/scripts/evaluate_model.py
```

Look for these key metrics:
- Accuracy: How often the model is correct overall
- F1 score: Balance between precision and recall
- Confusion matrix: Shows misclassification patterns

## Deploying Your Trained Model

Once satisfied with your model's performance:

```bash
# For Ollama-based model
# Your model is already available through Ollama API

# For PyTorch-based model
# The model is saved at ~/shinigami_ml/models/
# The service will automatically use the latest model
```

## Tips for Better Training Results

1. **Balanced Dataset**: Ensure similar numbers of examples for each class
2. **Diverse Examples**: Include content from various platforms and contexts
3. **Ambiguous Cases**: Include plenty of "gray area" examples
4. **Regular Updates**: Retrain periodically as language evolves

## Troubleshooting

- **Out of Memory**: Reduce batch size in training script
- **Poor Accuracy**: Add more diverse training examples
- **Slow Training**: Consider using a smaller model like Gemma 2B instead
