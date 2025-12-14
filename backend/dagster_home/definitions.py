"""Dagster definitions for KYCC ML training pipeline."""

import sys
sys.path.insert(0, "/workspace")  # Ensure live-mounted code takes precedence

from dagster import Definitions, job, op, OpExecutionContext

from app.services.feature_matrix_builder import FeatureMatrixBuilder
from app.services.model_training_service import ModelTrainingService


@op(config_schema={"batch_id": str})
def build_matrix_op(context: OpExecutionContext):
	"""Build feature matrix and split train/test for a batch."""
	batch_id = context.op_config["batch_id"]
	builder = FeatureMatrixBuilder()
	X, y, metadata = builder.build_matrix(batch_id)
	X_train, X_test, y_train, y_test = builder.split_train_test(X, y, test_size=0.2, random_state=42)

	context.log.info(
		f"Built matrix for batch {batch_id}: train={len(X_train)}, test={len(X_test)}, labels={metadata.label_distribution}"
	)

	return {
		"X_train": X_train,
		"X_test": X_test,
		"y_train": y_train,
		"y_test": y_test,
		"metadata": metadata,
	}


@op
def train_and_evaluate_op(context: OpExecutionContext, datasets: dict):
	"""Train logistic regression and evaluate on test split."""
	svc = ModelTrainingService()
	model, train_metadata = svc.train_logistic_regression(
		datasets["X_train"], datasets["y_train"], hyperparams={"max_iter": 200}
	)
	metrics = svc.evaluate_model(model, datasets["X_test"], datasets["y_test"])

	context.log.info(f"Eval metrics: roc_auc={metrics.get('roc_auc'):.4f}, f1={metrics.get('f1'):.4f}")

	return {
		"model": model,
		"metrics": metrics,
		"train_metadata": train_metadata,
		"dataset_metadata": datasets.get("metadata"),
	}


@job
def training_pipeline():
	"""End-to-end training: build matrix -> train -> evaluate."""
	datasets = build_matrix_op()
	train_and_evaluate_op(datasets)


defs = Definitions(jobs=[training_pipeline])
