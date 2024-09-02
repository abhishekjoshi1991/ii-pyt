import os
from datetime import datetime
from transformers.trainer_callback import TrainerState

def latest_folds_dir(folds_dir):
    timestamps = os.listdir(folds_dir)
    latest_timestamp_str = max(timestamps, key=lambda ts: datetime.strptime(ts, '%Y%m%d_%H%M%S'))
    latest_folds_path = os.path.join(folds_dir, latest_timestamp_str)
    latest_best_model_path = best_model_path(latest_folds_path)
    return latest_best_model_path

def best_model_path(dir):
    best_checkpoint = None
    best_metric_value = float('inf')  # Initialize with a large value for loss-based metrics (e.g., validation loss)
    try:
        list_dir = sorted(os.listdir(dir), key=int)
        
        for folds_dir in list_dir:
            folds_path = os.path.join(dir, folds_dir)
            if not os.path.isdir(folds_path):
                continue

            # Iterate over each checkpoint directory within the folds directory
            for checkpoint_dir in os.listdir(folds_path):
                checkpoint_path = os.path.join(folds_path, checkpoint_dir)
                if not os.path.isdir(checkpoint_path):
                    continue

                # Load Trainer state from the checkpoint directory
                state_path = os.path.join(checkpoint_path, "trainer_state.json")
                if not os.path.exists(state_path):
                    continue

                state = TrainerState.load_from_json(state_path)

                # Retrieve the metric value of interest (e.g., validation loss) from log history
                for log in state.log_history:
                    if 'eval_loss' in log:
                        metric_value = log['eval_loss']  # Replace 'eval_loss' with the desired metric
                        #break

                # Update the best checkpoint if the current metric value is better
                if metric_value < best_metric_value:
                    best_metric_value = metric_value
                    best_checkpoint = checkpoint_path

        return best_checkpoint
    except ValueError:
        return dir
