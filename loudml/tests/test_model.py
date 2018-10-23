import unittest

import loudml.vendor

from loudml import (
    errors,
    schemas,
)
from loudml.model import (
    Feature,
    flatten_features,
    Model,
)

class TestModel(unittest.TestCase):
    def invalid_feature(self, **kwargs):
        with self.assertRaises(errors.Invalid):
            Feature(**kwargs)

    def test_validate_feature(self):
        # Valid
        Feature(
            name="foo",
            field="bar",
            metric="avg",
        )
        Feature(
            name="foo",
            field="bar",
            metric="avg",
            measurement="baz",
            default=0,
        )
        Feature(
            name="foo",
            field="prefix.bar",
            metric="avg",
            measurement="prefix.baz",
        )

        # Invalid
        self.invalid_feature(
            name="foo/invalid",
            field="bar",
            metric="avg",
        )
        self.invalid_feature(
            metric="avg",
            field="bar",
        )
        self.invalid_feature(
            name="foo",
            field="bar",
        )
        self.invalid_feature(
            name="foo",
            metric="avg",
        )
        self.invalid_feature(
            name="foo",
            metric="avg",
            field="bar",
            default="invalid",
        )

    def invalid_model(self, **kwargs):
        with self.assertRaises(errors.Invalid):
            Model(**kwargs)

    def test_validate_model(self):
        # Valid
        Model(
            settings={
                'name': "foo",
                'type': "generic",
                'features': [
                    {
                        'name': 'bar',
                        'field': 'baz',
                        'metric': 'avg',
                    },
                    {
                        'name': 'bar',
                        'field': 'baz',
                        'metric': 'count',
                    }
                ],
            }
        )
        Model(
            settings={
                'name': "foo",
                'type': "generic",
                'features': [
                    {
                        'name': 'bar',
                        'field': 'baz',
                        'metric': 'avg',
                    },
                ],
                'routing': 'cux',
            }
        )
        Model(
            settings={
                'name': "foo",
                'type': "generic",
                'features': [
                    {
                        'name': 'bar',
                        'measurement': 'prefix.measurement',
                        'field': 'prefix.baz',
                        'metric': 'avg',
                    },
                ],
                'routing': 'cux',
            }
        )

        # Invalid
        self.invalid_model(
            settings={
                'type': 'generic',
                'features': [
                    {
                        'name': 'bar',
                        'field': 'baz',
                        'metric': 'avg',
                    },
                ],
            }
        )
        self.invalid_model(
            settings={
                'name': 'foo',
                'type': 'generic',
                'features': [],
            }
        )
        self.invalid_model(
            settings={
                'name': 'foo/invalid',
                'type': 'generic',
                'features': [
                    {
                        'name': 'bar',
                        'field': 'baz',
                        'metric': 'avg',
                    },
                ],
            }
        )

    def test_flatten_features(self):
        res = flatten_features([
            {
                'name': 'foo',
                'field': 'foo',
                'metric': 'avg',
            },
        ])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['io'], 'io')

        res = flatten_features([
            {
                'name': 'foo',
                'field': 'foo',
                'metric': 'avg',
                'io': 'i',
            },
            {
                'name': 'bar',
                'field': 'bar',
                'metric': 'avg',
                'io': 'io',
            },
            {
                'name': 'baz',
                'field': 'baz',
                'metric': 'avg',
                'io': 'o',
            },
        ])
        self.assertEqual(res, [
            {
                'name': 'bar',
                'field': 'bar',
                'metric': 'avg',
                'io': 'io',
            },
            {
                'name': 'baz',
                'field': 'baz',
                'metric': 'avg',
                'io': 'o',
            },
            {
                'name': 'foo',
                'field': 'foo',
                'metric': 'avg',
                'io': 'i',
            },

        ])

        res = flatten_features({
            'io': [
                {
                    'name': 'foo',
                    'field': 'foo',
                    'metric': 'avg',
                },
            ],
            'o': [
                {
                    'name': 'bar',
                    'field': 'bar',
                    'metric': 'avg',
                },
            ],
            'i': [
                {
                    'name': 'baz',
                    'field': 'baz',
                    'metric': 'avg',
                },
            ]
        })
        self.assertEqual(res, [
            {
                'name': 'foo',
                'field': 'foo',
                'metric': 'avg',
                'io': 'io',
            },
            {
                'name': 'bar',
                'field': 'bar',
                'metric': 'avg',
                'io': 'o',
            },
            {
                'name': 'baz',
                'field': 'baz',
                'metric': 'avg',
                'io': 'i',
            },

        ])
