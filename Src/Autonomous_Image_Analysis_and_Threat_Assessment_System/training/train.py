import torch
from ultralytics import YOLO
import random
import numpy as np
import os

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def get_next_run_dir(base_dir, prefix='train'):
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    existing_runs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d.startswith(prefix)]
    run_numbers = [int(d[len(prefix):]) for d in existing_runs if d[len(prefix):].isdigit()]
    next_run = max(run_numbers) + 1 if run_numbers else 1
    return f"{prefix}{next_run}"

def main():
    # Set seed for reproducibility
    set_seed(42)

    # Determine device (use GPU if available)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")

    model = YOLO("yolov8m.pt")

    # Set up data and output directories
    data = "../datasets/vehicles/data.yaml"  # 'data.yaml' file will be loaded from here
    base_output_dir = '../datasets/vehicles/runs/detect'  # Outputs will be saved here

    # Determine the next run directory (e.g., train1, train2, ...)
    run_name = get_next_run_dir(base_output_dir, prefix='train')
    print(f"Training run will be saved to: {run_name}")

    # Training hyperparameters
    training_params = {
        'data': data,                  # Data configuration file
        'epochs': 100,                 # Number of training epochs
        'batch': 16,                   # Batch size (optimized for RTX 2060 Super)
        'imgsz': 640,                  # Image size
        'lr0': 0.01,                   # Initial learning rate
        'momentum': 0.937,             # Momentum
        'weight_decay': 0.0005,        # Weight decay
        'warmup_epochs': 3.0,          # Number of warmup epochs
        'warmup_momentum': 0.8,        # Warmup momentum value
        'warmup_bias_lr': 0.1,         # Warmup bias learning rate
        'box': 7.5,                    # Box loss weight
        'cls': 0.5,                    # Class loss weight
        'dfl': 1.5,                    # DFL loss weight
        'label_smoothing': 0.0,        # Label smoothing
        'cache': False,                # Data caching
        'workers': 8,                  # Number of DataLoader workers
        'save_period': -1,             # Model save period (-1: do not save periodically)
        'save': True,                  # Save the model
        'save_txt': False,             # Save results as txt
        'save_conf': False,            # Save prediction confidence scores
        'verbose': True,               # Verbose output
        'patience': 20,                # Patience for early stopping (number of epochs)
        'project': base_output_dir,    # Output directory
        'name': run_name,              # Run name (subdirectory)
        'exist_ok': False,             # Do not overwrite existing directories
    }

    # Pass training parameters to the model.train() function
    results = model.train(**training_params)

    # You can use model.eval() to evaluate the training results
    # Evaluation process can be added here

    # Save the best model
    best_model_path = os.path.join(base_output_dir, run_name, 'best.pt')
    if os.path.exists(best_model_path):
        print(f"Best model saved: {best_model_path}")
    else:
        print("Best model could not be saved.")

if __name__ == '__main__':
    main()
