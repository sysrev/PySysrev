import unittest
from unittest.mock import patch
from sysrev.client import Client

class TestClient(unittest.TestCase):
    def setUp(self):
        # Create a Client instance with a fake API key for testing
        self.client = Client(api_key='fake_api_key')

    @patch('sysrev.client.requests.get')
    def test_get_project_info(self, mock_get):
        # Configure the mock to return a JSON response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'project': {'id': 123, 'name': 'Test Project'}}

        # Call the function
        response = self.client.get_project_info(project_id=123)

        # Check that the requests.get was called correctly
        mock_get.assert_called_once_with(
            'https://www.sysrev.com/api-json/project-info',
            headers={'Authorization': 'Bearer fake_api_key'},
            params={'project-id': 123}
        )

        # Verify the response
        self.assertEqual(response, {'project': {'id': 123, 'name': 'Test Project'}})

    @patch('sysrev.client.requests.post')
    def test_set_labels(self, mock_post):
        # Configure the mock to return a JSON response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'success': True}

        # Dummy data for the test
        label_ids = [1, 2]
        label_values = ['yes', 'no']
        label_types = ['boolean', 'boolean']

        # Call the function
        response = self.client.set_labels(
            project_id=456, article_id=789, label_ids=label_ids,
            label_values=label_values, label_types=label_types,
            confirm=True, change=False, resolve=False
        )

        # Check that the requests.post was called correctly
        mock_post.assert_called_once()

        # Verify the response
        self.assertEqual(response, {'success': True})

if __name__ == '__main__':
    unittest.main()
