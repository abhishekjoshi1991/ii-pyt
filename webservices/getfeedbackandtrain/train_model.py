import os
import sys
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_path)
import torch
import datetime
from datasets import Dataset
from transformers import (
    AutoTokenizer, 
    GPT2LMHeadModel,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from sklearn.model_selection import KFold
from preprocess_wiki_content import PrepareModelDataset

dataset_obj = PrepareModelDataset()

def preprocess_function(examples, tokenizer):
    inputs = [q + " [SEP] " + a + "<|endoftext|>" for q, a in zip(examples["question"], examples["answer"])]
    model_inputs = tokenizer(inputs, max_length=1024, truncation=True, padding=True, return_tensors="pt")
    return model_inputs

class TrainModel():
    def __init__(self):
        self.n_splits = 5
        self.model_name = 'nlp-waseda/comet-gpt2-small-japanese'
        self.common_training_args = {
                        "evaluation_strategy": "epoch",
                        "save_strategy": "epoch",
                        "learning_rate": 3.842858232584513e-05,
                        "per_device_train_batch_size": 8,
                        "per_device_eval_batch_size": 8,
                        "num_train_epochs": 60,
                        "weight_decay": 0.058649705990444265,
                        "logging_steps": 10,
                        "load_best_model_at_end": True,
                        "metric_for_best_model": "eval_loss",
                        "greater_is_better": False,
                        "report_to": "none",
                        "save_total_limit": 3
                    }
        
    def load_dataset(self):
        dataset = dataset_obj.preprocess_data()
        dataset = dataset.rename(columns={'final_processed_content_x0001': 'answer'})
        dataset = dataset[['question', 'answer']]
        hf_dataset = Dataset.from_pandas(dataset)
        return hf_dataset
    
    def setup_model_and_tokenizer(self, model_name):
        model = GPT2LMHeadModel.from_pretrained(
            model_name,
            device_map="auto",
            trust_remote_code=True
        )
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.pad_token = tokenizer.eos_token
        return model, tokenizer
    
    def train_evaluate_model(self, hf_dataset, model, tokenizer, n_splits, common_training_args, timestamp):
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
        model_save_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 'model_files')
        fold_results = []
        for fold, (train_idx, val_idx) in enumerate(kf.split(hf_dataset)):
            print(f"\nTraining on fold {fold+1}")

            hf_dataset = hf_dataset.shuffle(seed=42)
            train_dataset = hf_dataset.select(train_idx)
            val_dataset = hf_dataset.select(val_idx)

            tokenized_train_dataset = train_dataset.map(lambda x: preprocess_function(x, tokenizer), batched=True)
            tokenized_val_dataset = val_dataset.map(lambda x: preprocess_function(x, tokenizer), batched=True)

            # Update training arguments for this fold
            training_args = TrainingArguments(
                output_dir=f"{model_save_path}/{timestamp}/{fold+1}",
                **common_training_args,
            )

            # Initialize Trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_train_dataset,
                eval_dataset=tokenized_val_dataset,
                tokenizer=tokenizer,
                data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
            )
            model.config.use_cache = False
            try:
                trainer.train()
            except torch.cuda.OutOfMemoryError:
                return "CUDA out of memory during training!"


            best_ckpt_path = trainer.state.best_model_checkpoint
            print('best_ckpt_path =============', best_ckpt_path)
            
            torch.save(model.state_dict(), f"{best_ckpt_path}/model_state_dict.pth")

            # Evaluate the model on the validation set
            eval_results = trainer.evaluate()
            fold_results.append(eval_results)

            # Extract training loss from log history
            training_loss = [log['loss'] for log in trainer.state.log_history if 'loss' in log][-1]
            print(f"Fold {fold+1} Training Loss: {training_loss}")
            print(f"Fold {fold+1} Evaluation Results: {eval_results}")
            
            
        print("Evaluation losses for each fold:", [result['eval_loss'] for result in fold_results])

        best_fold_index = fold_results.index(min(fold_results, key=lambda x: x['eval_loss']))
        print(f"Best Fold: {best_fold_index + 1} with eval_loss: {fold_results[best_fold_index]['eval_loss']}")

        best_ckpt_path2 = trainer.state.best_model_checkpoint
        print('best_ckpt_path 2=============', best_ckpt_path2)
        return fold_results

    def train(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset = self.load_dataset()
        model, tokenizer = self.setup_model_and_tokenizer(self.model_name)
        self.train_evaluate_model(dataset, model, tokenizer, self.n_splits, self.common_training_args, timestamp)
    
obj = TrainModel()
obj.train()