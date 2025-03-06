# training/train.py
import torch
from ultralytics import YOLO
import random
import numpy as np
import os

class TrainModule:
    def __init__(self, 
                 seed=42,
                 model_path="yolov8m.pt",
                 data_config="../datasets/merged_datasets/data.yaml",
                 base_output_dir='../datasets/merged_datasets/runs/detect',
                 prefix='train',
                 training_params=None):
        """
        Initializes the training module with default or provided parameters.
        """
        self.seed = seed
        self.model_path = model_path
        self.data_config = data_config
        self.base_output_dir = base_output_dir
        self.prefix = prefix
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.run_name = self.get_next_run_dir()
        
        # Default training parameters
        default_params = {
            'epochs': 50,
            'batch': 16,
            'imgsz': 640,
            'lr0': 0.01,
            'momentum': 0.937,
            'weight_decay': 0.0005,
            'warmup_epochs': 3.0,
            'warmup_momentum': 0.8,
            'warmup_bias_lr': 0.1,
            'box': 7.5,
            'cls': 0.5,
            'dfl': 1.5,
            'label_smoothing': 0.0,
            'cache': False,
            'workers': 8,
            'save_period': -1,
            'save': True,
            'save_txt': False,
            'save_conf': False,
            'verbose': True,
            'patience': 20,
            'project': self.base_output_dir,
            'name': self.run_name,
            'exist_ok': False,
        }
        
        # Update default parameters with any provided parameters
        if training_params:
            default_params.update(training_params)
        
        self.training_params = default_params

    def set_seed(self):
        """
        Sets the seed for reproducibility.
        """
        random.seed(self.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)
        print(f"Seed set to: {self.seed}")

    def get_next_run_dir(self):
        """
        Determines the next run directory based on existing runs.
        """
        if not os.path.exists(self.base_output_dir):
            os.makedirs(self.base_output_dir)
            print(f"Created base output directory: {self.base_output_dir}")
        
        existing_runs = [
            d for d in os.listdir(self.base_output_dir)
            if os.path.isdir(os.path.join(self.base_output_dir, d)) and d.startswith(self.prefix)
        ]
        run_numbers = [
            int(d[len(self.prefix):]) for d in existing_runs
            if d[len(self.prefix):].isdigit()
        ]
        next_run = max(run_numbers) + 1 if run_numbers else 1
        run_name = f"{self.prefix}{next_run}"
        print(f"Next run directory determined: {run_name}")
        return run_name

    def load_model(self):
        """
        Loads the YOLO model.
        """
        model = YOLO(self.model_path)
        print(f"Model loaded from {self.model_path}")
        return model

    def train(self):
        """
        Executes the training process.
        """
        self.set_seed()
        print(f"Using device: {self.device}")
        
        model = self.load_model()
        
        print(f"Training run will be saved to: {self.run_name}")
        
        # Move model to the appropriate device
        model.to(self.device)
        
        # Start training
        print("Starting training...")
        results = model.train(**self.training_params)
        print("Training completed.")
        
        # Save the best model
        best_model_path = os.path.join(self.base_output_dir, self.run_name, 'best.pt')
        if os.path.exists(best_model_path):
            print(f"Best model saved at: {best_model_path}")
        else:
            print("Best model could not be saved.")

    def evaluate(self):
        """
        Evaluates the trained model. Placeholder for evaluation logic.
        """
        # Implement evaluation logic here
        print("Evaluation is not yet implemented.")

def main():
    # Initialize the training module with default parameters
    trainer = TrainModule()
    
    # Start training
    trainer.train()
    
    # Optionally, evaluate the model
    # trainer.evaluate()

if __name__ == '__main__':
    main()
