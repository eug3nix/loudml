import datetime
import logging
import os
import random
import numpy as np
import time
import unittest

logging.getLogger('tensorflow').disabled = True

from loudml import (
    errors,
)

from loudml.misc import (
    list_from_np,
    ts_to_str,
)

from loudml.randevents import SinEventGenerator

from loudml.timeseries import (
    TimeSeriesModel,
)
from loudml.warp10 import (
    Warp10DataSource,
)

SCW_READ_TOKEN = "RpOCNdxiepotjQzfGub95Te42z5E8XbjfzCe.Q_heDurpC6qVdn4JLiCO_VDJq20SCOG3AtwvvxVqxBWcQnsLEkIRUtYWHplcaI80QGaUBre9aBIyxD7TGAF0a55QTiGapNm7G3KU0BfBYKwUYwp3vkHe7WVo0Zx"
SCW_WRITE_TOKEN = "q3pnfOmr7NG5Rp1W1jXEDkzSwN9BFRL67Kl9yBGgq64va8H6tmUqwWDt5Yv_iSYwdy5rTJ2I9YToEc.4XUKDXPJtk_EMW7w_pvOcYLpqzQvzP8eJd7ZHf.cesGjmEFzB"

class TestWarp10(unittest.TestCase):
    def setUp(self):
        self.source = Warp10DataSource({
            'name': 'test',
            'url': os.environ.get('url', 'http://test-warp10.loudml.io:8080/api/v0'),
            'read_token': os.environ.get('WARP10_READ_TOKEN', SCW_READ_TOKEN),
            'write_token': os.environ.get('WARP10_WRITE_TOKEN', SCW_WRITE_TOKEN),
        })
        logger = logging.getLogger('warp10client.client')
        logger.setLevel(logging.INFO)

        self.tag = {'test': str(datetime.datetime.now().timestamp())}

        self.model = TimeSeriesModel(dict(
            name="test-model",
            offset=30,
            span=300,
            bucket_interval=3600,
            interval=60,
            features=[
                {
                    'name': 'avg_foo',
                    'metric': 'avg',
                    'measurement': 'measure1',
                    'field': 'foo',
                },
                {
                    'name': 'count_bar',
                    'metric': 'count',
                    'measurement': 'measure2',
                    'field': 'bar',
                    'default': 0,
                },
            ],
            threshold=30,
        ))

        self.t0 = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ).timestamp()

    def tearDown(self):
        self.source.drop(tags=self.tag)

    def test_multi_fetch(self):
        res = self.source.build_multi_fetch(
            self.model,
            "2018-07-21T00:00:00Z",
            "2018-07-22T00:00:00Z",
            tags={'key': 'value'},
        )
        self.assertEqual(
            res,
"""
[
[
[
'{}'
'foo'
{{ 'key' 'value' }}
'2018-07-21T00:00:00Z'
'2018-07-22T00:00:00Z'
]
FETCH
bucketizer.mean
0
3600000000
0
]
BUCKETIZE
[
[
'{}'
'bar'
{{ 'key' 'value' }}
'2018-07-21T00:00:00Z'
'2018-07-22T00:00:00Z'
]
FETCH
bucketizer.count
0
3600000000
0
]
BUCKETIZE
]
""".strip().format(self.source.read_token, self.source.read_token)
        )

    def test_write_read(self):
        t0 = self.t0

        self.source.insert_times_data(
            ts=t0 - 7000,
            data={'foo': 0.7},
            tags=self.tag,
        )
        self.source.insert_times_data(
            ts=t0 - 3800,
            data={'bar': 42},
            tags=self.tag,
        )
        self.source.insert_times_data(
            ts=t0 - 1400,
            data={
                'foo': 0.8,
                'bar': 33,
            },
            tags=self.tag,
        )
        self.source.insert_times_data(
            ts=t0 - 1200,
            data={
                'foo': 0.4,
                'bar': 64,
            },
            tags=self.tag,
        )
        self.source.commit()

        period_len = 3 * self.model.bucket_interval

        res = self.source.get_times_data(
            self.model,
            t0 - period_len,
            t0,
            tags=self.tag,
        )

        self.assertEqual(len(res), period_len / self.model.bucket_interval)

        bucket = res[0][1]
        self.assertEqual(list_from_np(bucket), [None, None])
        bucket = res[1][1]
        self.assertEqual(bucket, [0.7, 1.0])
        bucket = res[2][1]
        self.assertAlmostEqual(bucket[0], 0.6)
        self.assertEqual(bucket[1], 2.0)

    def test_no_data(self):
        with self.assertRaises(errors.NoData):
            self.source.get_times_data(
                self.model,
                "2017-01-01T00:00:00Z",
                "2017-01-31T00:00:00Z",
            )

    def test_match_all(self):
        model = TimeSeriesModel(dict(
            name="test-model",
            offset=30,
            span=300,
            bucket_interval=3,
            interval=60,
            features=[
                {
                    'name': 'avg_foo',
                    'metric': 'avg',
                    'measurement': 'measure3',
                    'field': 'foo',
                    'match_all': [
                        {'tag': 'tag_1', 'value': 'tag_A'},
                    ],
                },
            ],
            threshold=30,
        ))

        t0 = self.t0

        data = [
            # (foo, timestamp)
            (33, t0 - 1), # excluded
            # empty
            (120, t0 + 1), (312, t0 + 2),
            (18, t0 + 7),
            (78, t0 + 10), # excluded
        ]
        for foo, ts in data:
            self.source.insert_times_data(
                ts=ts,
                data={
                    'foo': foo,
                }
            )
            self.source.insert_times_data(
                ts=ts,
                tags={
                    'tag_1': 'tag_A',
                    'tag_2': 'tag_B',
                },
                data={
                    'foo': foo,
                }
            )
            self.source.insert_times_data(
                ts=ts,
                tags={
                    'tag_1': 'tag_B',
                    'tag_2': 'tag_C',
                },
                data={
                    'foo': -foo,
                }
            )

        self.source.commit()
        time.sleep(5)

        res = self.source.get_times_data(
            model,
            from_date=t0,
            to_date=t0 + 3 * model.bucket_interval,
        )
        foo_avg = []
        for line in res:
            foo_avg.append(line[1][0])

        np.testing.assert_allclose(
            np.array(foo_avg),
            np.array([216.0, np.nan, 18.0]),
            rtol=0,
            atol=0,
        )

        model = TimeSeriesModel(dict(
            name="test-model",
            offset=30,
            span=300,
            bucket_interval=3,
            interval=60,
            features=[
                {
                    'name': 'avg_foo',
                    'metric': 'avg',
                    'field': 'foo',
                    'match_all': [
                        {'tag': 'tag_1', 'value': 'tag_B'},
                    ],
                },
            ],
            threshold=30,
        ))

        res = self.source.get_times_data(
            model,
            from_date=self.t0,
            to_date=t0 + 3 * model.bucket_interval,
        )
        avg_foo = []
        for line in res:
            avg_foo.append(line[1][0])

        np.testing.assert_allclose(
            np.array(avg_foo),
            np.array([-216.0, np.nan, -18.0]),
            rtol=0,
            atol=0,
        )

    def test_train(self):

        generator = SinEventGenerator(base=3, sigma=0.05)

        to_date = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ).timestamp()
        from_date = to_date - 3600 * 24

        for ts in generator.generate_ts(from_date, to_date, step_ms=60000):
            self.source.insert_times_data(
                measurement='measure1',
                ts=ts,
                tags=self.tag,
                data={
                    'foo': random.lognormvariate(10, 1)
                },
            )

        self.source.commit()
        time.sleep(5)

        # Train
        model.train(self.source, from_date=from_date, to_date=to_date)

        # Check
        self.assertTrue(model.is_trained)