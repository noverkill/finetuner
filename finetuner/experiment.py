from typing import Any, Dict, List, Optional, Union

from docarray import DocumentArray

from finetuner.client import FinetunerV1Client
from finetuner.constants import (
    BATCH_SIZE,
    CONFIG,
    CREATED_AT,
    DATA,
    DESCRIPTION,
    EPOCHS,
    EVAL_DATA,
    EXPERIMENT_NAME,
    FREEZE,
    HYPER_PARAMETERS,
    IMAGE_MODALITY,
    LEARNING_RATE,
    LOSS,
    MINER,
    MODEL,
    MULTI_MODAL,
    NAME,
    OPTIMIZER,
    OPTIMIZER_OPTIONS,
    OUTPUT_DIM,
    RUN_NAME,
    SCHEDULER_STEP,
    TEXT_MODALITY,
    TRAIN_DATA,
)
from finetuner.hubble import push_data_to_hubble
from finetuner.names import get_random_name
from finetuner.run import Run


class Experiment:
    """Class for an experiment.

    :param client: Client object for sending api requests.
    :param name: Name of the experiment.
    :param status: Status of the experiment.
    :param created_at: Creation time of the experiment.
    :param description: Optional description of the experiment.
    """

    def __init__(
        self,
        client: FinetunerV1Client,
        name: str,
        status: str,
        created_at: str,
        description: Optional[str] = '',
    ):
        self._client = client
        self._name = name
        self._status = status
        self._created_at = created_at
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> str:
        return self._status

    def get_run(self, name: str) -> Run:
        """Get a run by its name.

        :param name: Name of the run.
        :return: A `Run` object.
        """
        run_info = self._client.get_run(experiment_name=self._name, run_name=name)
        run = Run(
            name=run_info[NAME],
            config=run_info[CONFIG],
            created_at=run_info[CREATED_AT],
            description=run_info[DESCRIPTION],
            experiment_name=self._name,
            client=self._client,
        )
        return run

    def list_runs(self) -> List[Run]:
        """List every run inside the experiment.

        :return: List of `Run` objects.
        """
        run_infos = self._client.list_runs(experiment_name=self._name)
        return [
            Run(
                name=run_info[NAME],
                config=run_info[CONFIG],
                created_at=run_info[CREATED_AT],
                description=run_info[DESCRIPTION],
                experiment_name=self._name,
                client=self._client,
            )
            for run_info in run_infos
        ]

    def delete_run(self, name: str):
        """Delete a run by its name.

        :param name: Name of the run.
        """
        self._client.delete_run(experiment_name=self._name, run_name=name)

    def delete_runs(self):
        """Delete every run inside the experiment."""
        self._client.delete_runs(experiment_name=self._name)

    def create_run(
        self,
        model: str,
        train_data: Union[DocumentArray, str],
        run_name: Optional[str] = None,
        **kwargs,
    ) -> Run:
        """Create a run inside the experiment.

        :param model: Name of the model to be fine-tuned.
        :param train_data: Either a `DocumentArray` for training data or a
            name of the `DocumentArray` that is pushed on Hubble.
        :param run_name: Optional name of the run.
        :param kwargs: Optional keyword arguments for the run config.
        :return: A `Run` object.
        """
        if not run_name:
            run_name = get_random_name()
        train_data = push_data_to_hubble(
            client=self._client,
            data=train_data,
            data_type=TRAIN_DATA,
            experiment_name=self._name,
            run_name=run_name,
        )
        if kwargs.get(EVAL_DATA):
            kwargs[EVAL_DATA] = push_data_to_hubble(
                client=self._client,
                data=kwargs.get(EVAL_DATA),
                data_type=EVAL_DATA,
                experiment_name=self._name,
                run_name=run_name,
            )
        config = self._create_config_for_run(
            model=model,
            train_data=train_data,
            experiment_name=self._name,
            run_name=run_name,
            **kwargs,
        )
        run_info = self._client.create_run(
            run_name=run_name,
            experiment_name=self._name,
            run_config=config,
        )
        run = Run(
            client=self._client,
            name=run_info[NAME],
            experiment_name=self._name,
            config=run_info[CONFIG],
            created_at=run_info[CREATED_AT],
            description=run_info[DESCRIPTION],
        )
        return run

    @staticmethod
    def _create_config_for_run(
        model: str,
        train_data: str,
        experiment_name: str,
        run_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create config for a run.

        :param model: Name of the model to be fine-tuned.
        :param train_data: Either a `DocumentArray` for training data or a
            name of the `DocumentArray` that is pushed on Hubble.
        :param experiment_name: Name of the experiment.
        :param run_name: Name of the run.
        :param kwargs: Optional keyword arguments for the run config.
        :return: Run parameters wrapped up as a config dict.
        """
        return {
            MODEL: {
                NAME: model,
                FREEZE: kwargs.get(FREEZE),
                OUTPUT_DIM: kwargs.get(OUTPUT_DIM),
                MULTI_MODAL: kwargs.get(MULTI_MODAL),
            },
            DATA: {
                TRAIN_DATA: train_data,
                EVAL_DATA: kwargs.get(EVAL_DATA),
                IMAGE_MODALITY: kwargs.get(IMAGE_MODALITY),
                TEXT_MODALITY: kwargs.get(TEXT_MODALITY),
            },
            HYPER_PARAMETERS: {
                LOSS: kwargs.get(LOSS),
                OPTIMIZER: kwargs.get(OPTIMIZER),
                OPTIMIZER_OPTIONS: {},
                MINER: kwargs.get(MINER),
                BATCH_SIZE: kwargs.get(BATCH_SIZE),
                LEARNING_RATE: kwargs.get(LEARNING_RATE),
                EPOCHS: kwargs.get(EPOCHS),
                SCHEDULER_STEP: kwargs.get(SCHEDULER_STEP),
            },
            EXPERIMENT_NAME: experiment_name,
            RUN_NAME: run_name,
        }