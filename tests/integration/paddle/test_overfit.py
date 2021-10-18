import paddle
import pytest
from paddle import nn
from scipy.spatial.distance import pdist, squareform

from finetuner.tuner.paddle import PaddleTuner


@pytest.mark.parametrize(
    "n_cls,dim,n_samples,n_epochs,batch_size,loss",
    [
        (5, 10, 100, 5, 25, 'EuclideanTripletLoss'),
        (5, 10, 100, 5, 25, 'CosineTripletLoss'),
        # Siamese needs more time to convereg
        (5, 10, 1000, 15, 256, 'EuclideanSiameseLoss'),
        (5, 10, 1000, 15, 256, 'CosineSiameseLoss'),
    ],
)
def test_overfit_paddle(
    create_easy_data,
    n_cls: int,
    dim: int,
    n_samples: int,
    n_epochs: int,
    batch_size: int,
    loss: str,
):
    """This test makes sure that we can overfit the model to a small amount of data.

    We use an over-parametrized model (a few thousand weights for <100 unique input
    vectors), which should easily be able to bring vectors from same class
    together, and put those from different classes apart - note that all the vectors
    are random.
    """

    # Prepare model and data
    data, vecs = create_easy_data(n_cls, dim, n_samples)
    embed_model = nn.Sequential(
        nn.Flatten(),
        nn.Linear(in_features=dim, out_features=64),
        nn.ReLU(),
        nn.Linear(in_features=64, out_features=64),
        nn.ReLU(),
        nn.Linear(in_features=64, out_features=64),
        nn.ReLU(),
        nn.Linear(in_features=64, out_features=32),
    )

    # Train
    pt = PaddleTuner(embed_model, loss=loss)
    pt.fit(train_data=data, epochs=n_epochs, batch_size=batch_size)

    # Compute embedding for original vectors
    vec_embedings = embed_model(paddle.Tensor(vecs)).numpy()

    # Compute distances between embeddings
    metric = 'sqeuclidean' if 'Euclidean' in loss else 'cosine'
    dists = squareform(pdist(vec_embedings, metric=metric))

    # Make sure that for each class, the two instances are closer than
    # anything else
    for i in range(n_cls):
        cls_dist = dists[2 * i, 2 * i + 1]
        dist_other = dists[2 * i : 2 * i + 2, :].copy()
        dist_other[:, 2 * i : 2 * i + 2] = 10_000

        assert cls_dist < dist_other.min() + 1