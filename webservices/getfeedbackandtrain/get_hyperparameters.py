import os
import sys
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_path)
from datasets import Dataset
from transformers import TrainerCallback
from ray import tune, init, shutdown, train
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from preprocess_wiki_content import PrepareModelDataset
dataset_obj = PrepareModelDataset()


class TuneReportCallback(TrainerCallback):
    """Custom Callback for Hugging Face Trainer to report metrics to Ray Tune using ray.train.report."""
    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        train.report({"eval_loss": metrics["eval_loss"]})

def tokenize_function(tokenizer, examples):
    concatenated_texts = [q + " [SEP] " + a + "<|endoftext|>" for q, a in zip(examples["Question"], examples["Answer"])]
    inputs = tokenizer(concatenated_texts, max_length=512, truncation=True, padding="max_length", return_tensors="pt")
    return inputs

def tokenize_and_prepare_datasets(tokenizer, data):
    try:
        tokenized_data = [tokenize_function(tokenizer, row) for _, row in data.iterrows()]

        dataset = Dataset.from_dict({
            "input_ids": [x["input_ids"][0] for x in tokenized_data],
            "attention_mask": [x["attention_mask"][0] for x in tokenized_data],
            "labels": [x["input_ids"][0] for x in tokenized_data]
        })
        return dataset
    except Exception as e:
        print(f"Failed to tokenize and prepare datasets: {e}")
        raise

def train_model(config, train_data, test_data):
    output_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 'hpt_logs/output')
    log_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 'hpt_logs/logs')

    tokenizer = AutoTokenizer.from_pretrained("nlp-waseda/comet-gpt2-small-japanese")
    model = AutoModelForCausalLM.from_pretrained("nlp-waseda/comet-gpt2-small-japanese")

    train_dataset = tokenize_and_prepare_datasets(tokenizer, train_data)
    test_dataset = tokenize_and_prepare_datasets(tokenizer, test_data)

    training_args = TrainingArguments(
        output_dir=output_dir,
        learning_rate=config["learning_rate"],
        per_device_train_batch_size=config["per_device_train_batch_size"],
        num_train_epochs=config["num_epochs"],
        do_eval=True,
        evaluation_strategy="epoch",
        logging_dir=log_dir,
        logging_steps=10,
        weight_decay=config["weight_decay"],
        save_total_limit=3
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        callbacks=[TuneReportCallback()]
    )

    trainer.train()

def get_hpt():
    result_df = dataset_obj.preprocess_data()
    result_df = result_df.rename(columns={'question': 'Question', 'final_processed_content_x0001': 'Answer'})
    result_df = result_df[['Question', 'Answer']]
    train_data, test_data = train_test_split(result_df, train_size=0.8, random_state=42)
    # train_data, test_data = load_and_prepare_data(file_path)
    search_space = {
        "learning_rate": tune.loguniform(1e-5, 5e-5),
        "per_device_train_batch_size": tune.choice([2,4,8]),
        "num_epochs": tune.choice([50]),
        "weight_decay": tune.uniform(0.0, 0.3)
    }

    init(ignore_reinit_error=True)

    analysis = tune.run(
        # train_model,
        tune.with_parameters(train_model, train_data=train_data, test_data=test_data),
        config=search_space,
        num_samples=3,
        resources_per_trial={'cpu': 1, 'gpu': 1},
        progress_reporter=tune.CLIReporter(parameter_columns=["learning_rate", "per_device_train_batch_size", "num_epochs"]),
        metric="eval_loss",
        mode="min",
        verbose=3,
    )

    best_config = analysis.get_best_config(metric="eval_loss", mode="min")
    print("Best hyperparameters found were: ", best_config)
    return best_config

if __name__ == "__main__":
    get_hpt()