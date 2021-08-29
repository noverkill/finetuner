from typing import Optional

import paddle
from jina.logging.profile import ProgressBar
from paddle import nn
from paddle.io import DataLoader
from paddle.optimizer import Optimizer

from . import head_layers, datasets
from ..base import BaseTuner, BaseHead, BaseArityModel, DocumentArrayLike
from ..dataset.helper import get_dataset


class _ArityModel(BaseArityModel, nn.Layer):
    ...


class PaddleTuner(BaseTuner):
    @property
    def head_layer(self) -> BaseHead:
        if isinstance(self._head_layer, str):
            return getattr(head_layers, self._head_layer)
        elif isinstance(self._head_layer, nn.Layer):
            return self._head_layer

    @property
    def wrapped_model(self) -> nn.Layer:
        if self.base_model is None:
            raise ValueError(f'base_model is not set')

        return self.head_layer(_ArityModel(self.base_model))  # wrap with head layer

    def _get_data_loader(self, inputs, batch_size: int, shuffle: bool):
        ds = get_dataset(datasets, self.arity)
        return DataLoader(
            dataset=ds(inputs=inputs),
            batch_size=batch_size,
            shuffle=shuffle,
        )

    def _eval(self, data, description: str = 'Evaluating'):
        self.wrapped_model.eval()

        losses = []
        metrics = []

        get_desc_str = (
            lambda: f'Loss={float(sum(losses) / len(losses)):.2f} Accuracy={float(sum(metrics) / len(metrics)):.2f}'
        )

        with ProgressBar(description, message_on_done=get_desc_str) as p:
            for inputs, label in data:
                outputs = self.wrapped_model(*inputs)
                loss = self.wrapped_model.loss_fn(outputs, label)
                metric = self.wrapped_model.metric_fn(outputs, label)

                losses.append(loss.item())
                metrics.append(metric.numpy())

                p.update(message=get_desc_str())

    def _train(self, data, optimizer: Optimizer, description: str):

        self.wrapped_model.train()

        losses = []
        metrics = []

        get_desc_str = (
            lambda: f'Loss={float(sum(losses) / len(losses)):.2f} Accuracy={float(sum(metrics) / len(metrics)):.2f}'
        )

        with ProgressBar(description, message_on_done=get_desc_str) as p:
            for inputs, label in data:
                # forward step
                outputs = self.wrapped_model(*inputs)
                loss = self.wrapped_model.loss_fn(outputs, label)
                metric = self.wrapped_model.metric_fn(outputs, label)

                optimizer.clear_grad()

                loss.backward()
                optimizer.step()

                losses.append(loss.item())
                metrics.append(metric.numpy())

                p.update(message=get_desc_str())

    def fit(
        self,
        train_data: DocumentArrayLike,
        eval_data: Optional[DocumentArrayLike] = None,
        epochs: int = 10,
        batch_size: int = 256,
        **kwargs,
    ):
        model = self.wrapped_model

        optimizer = paddle.optimizer.RMSProp(
            learning_rate=0.01, parameters=model.parameters()
        )

        for epoch in range(epochs):
            _data = self._get_data_loader(
                inputs=train_data, batch_size=batch_size, shuffle=False
            )

            self._train(
                _data,
                optimizer,
                description=f'Epoch {epoch + 1}/{epochs}',
            )

            if eval_data:
                _data = self._get_data_loader(
                    inputs=eval_data, batch_size=batch_size, shuffle=False
                )

                self._eval(_data)

    def save(self, *args, **kwargs):
        paddle.save(self.base_model.state_dict(), *args, **kwargs)