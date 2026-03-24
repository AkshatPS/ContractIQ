import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data folders
DATA_DIR = os.path.join(BASE_DIR, "data")

INPUTS_DIR = os.path.join(DATA_DIR, "inputs")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
TEMP_DIR = os.path.join(DATA_DIR, "temp")

VECTORSTORE_DIR = os.path.join(BASE_DIR, "vectorstore")

# Outputs
OUTPUTS_DIR = os.path.join(DATA_DIR, "outputs")
CLASSIFIED_DIR = os.path.join(OUTPUTS_DIR, "classified")
REPORTS_DIR = os.path.join(OUTPUTS_DIR, "reports")

# Model
MODEL_PATH = os.path.join(BASE_DIR, "models", "contract_clause_classifier")