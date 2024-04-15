import unittest
from sysrev.client import LabelTransformer

class TestLabelTransformer(unittest.TestCase):
    def test_handle_boolean_true(self):
        lt = LabelTransformer()
        self.assertTrue(lt.handle_boolean('yes'))

    def test_handle_boolean_false(self):
        lt = LabelTransformer()
        self.assertFalse(lt.handle_boolean('no'))

    def test_handle_boolean_raises(self):
        lt = LabelTransformer()
        with self.assertRaises(ValueError):
            lt.handle_boolean('maybe')

    def test_handle_categorical_or_string_single(self):
        lt = LabelTransformer()
        self.assertEqual(lt.handle_categorical_or_string('test'), ['test'])

    def test_handle_categorical_or_string_list(self):
        lt = LabelTransformer()
        self.assertEqual(lt.handle_categorical_or_string(['test', 'test2']), ['test', 'test2'])

    def test_handle_categorical_or_string_raises(self):
        lt = LabelTransformer()
        with self.assertRaises(ValueError):
            lt.handle_categorical_or_string(['test', 123])

if __name__ == '__main__':
    unittest.main()
