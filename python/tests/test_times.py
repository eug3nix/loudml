import datetime
import logging
import math
import os
import random
import unittest

logging.getLogger('tensorflow').disabled = True

from loudml_new.randevents import SinEventGenerator
from loudml_new.times import TimesModel
from loudml_new.memdatasource import MemDataSource
from loudml_new.memstorage import MemStorage

FEATURES = [
    {
        'name': 'count_foo',
        'metric': 'count',
        'field': 'foo',
        'nan_is_zero': True,
    },
    {
        'name': 'avg_foo',
        'metric': 'avg',
        'field': 'foo',
        'nan_is_zero': False,
    },
]

class TestTimes(unittest.TestCase):
    def setUp(self):
        self.source = MemDataSource()
        self.storage = MemStorage()
        self.model = None

        generator = SinEventGenerator(avg=3, sigma=0.05)

        self.to_date = datetime.datetime.now().timestamp()
        self.from_date = self.to_date - 3600 * 24 * 7

        for ts in generator.generate_ts(self.from_date, self.to_date, step=600):
            self.source.insert_times_data('test', {
                'timestamp': ts,
                'foo': random.normalvariate(10, 1)
            })

    def _require_training(self):
        if self.model:
            return

        self.model = TimesModel(dict(
            name='test',
            index='test',
            offset=30,
            span=20,
            bucket_interval=20 * 60,
            interval=60,
            features=FEATURES,
            threshold=30,
            max_evals=10,
        ))
        self.model.train(self.source)

    def test_train(self):
        self._require_training()
        self.assertTrue(self.model.is_trained)

    def test_format(self):
        import numpy as np

        data = [0, 2, 4, 6, 8, 10, 12, 14]
        dataset = np.zeros((8, 1), dtype=float)
        for i, val in enumerate(data):
            dataset[i] = val

        model = TimesModel(dict(
            name='test_fmt',
            index='test_fmt',
            offset=30,
            span=3,
            bucket_interval=20 * 60,
            interval=60,
            features=FEATURES,
            threshold=30,
            max_evals=10,
        ))

        indexes, x, y = model._format_dataset(dataset)

        self.assertEqual(indexes.tolist(), [3, 4, 5, 6, 7])
        self.assertEqual(x.tolist(), [
            [[0], [2], [4]],
            [[2], [4], [6]],
            [[4], [6], [8]],
            [[6], [8], [10]],
            [[8], [10], [12]],
        ])
        self.assertEqual(y.tolist(), [[6], [8], [10], [12], [14]])

    def test_train(self):
        self._require_training()
        self.assertTrue(self.model.is_trained)