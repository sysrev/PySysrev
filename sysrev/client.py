import requests

class LabelTransformer:
    
    def handle_boolean(self, label_value):
        if isinstance(label_value, bool):
            return label_value
        elif str(label_value).lower() in ['yes', 'no']:
            return str(label_value).lower() == 'yes'
        else:
            raise ValueError("Invalid boolean value")

    def handle_categorical_or_string(self, label_value):
        if isinstance(label_value, str):
            return [label_value]
        elif isinstance(label_value, list) and all(isinstance(item, str) for item in label_value):
            return label_value
        else:
            raise ValueError("Invalid value for categorical or string type")

    def transform_label(self, label_type, label_value):
        if label_type == 'boolean':
            return self.handle_boolean(label_value)
        elif label_type in ['categorical', 'string']:
            return self.handle_categorical_or_string(label_value)
        else:
            raise ValueError("Invalid label type")
        
class Client():
    
    def __init__(self, api_key, base_url="https://www.sysrev.com"):
        self.api_key = api_key
        self.base_url = base_url
    
    def get_project_info(self, project_id):
        endpoint = f"{self.base_url}/api-json/project-info"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(endpoint, headers=headers, params={"project-id": project_id})
        return response.json()

    def set_labels(self, project_id, article_id, label_ids, label_values, label_types, confirm=False, change=False, resolve=False):
        endpoint = f"{self.base_url}/api-json/set-labels"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        assert len(label_ids) == len(label_values) == len(label_types), "Length of label_ids, label_values, and label_types should be the same."
        
        # construct label_values_dict
        tf = LabelTransformer()
        label_values_dict = {label_ids[i]: tf.transform_label(label_types[i], label_values[i]) for i in range(len(label_ids))}    
        
        # Constructing the data payload as per the server's expectation
        data = {"project-id": project_id, "article-id": article_id, "label-values": label_values_dict}
        data.update({ "confirm?": confirm, "change?": change, "resolve?": resolve })
        
        # Sending a POST request to the server
        response = requests.post(endpoint, json=data, headers=headers)
        return response.json()
    
    def get_project_articles(self, project_id, offset=0, limit=10, sort_by=None, sort_dir=None):
        endpoint = f"{self.base_url}/api-json/project-articles"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {"project-id": project_id, "n-offset": offset, "n-count": limit}
        
        # Add optional sorting keys if provided
        if sort_by: body["sort-by"] = sort_by
        if sort_dir: body["sort-dir"] = sort_dir

        # Make the POST request with the simplified body
        response = requests.post(endpoint, headers=headers, json=body)
        return response.json()
    
    def fetch_all_articles(self, project_id, limit=10, sort_by=None, sort_dir=None):
        offset = 0
        while True:
            result = self.get_project_articles(project_id, offset=offset, limit=limit, sort_by=sort_by, sort_dir=sort_dir)
            articles = result.get('result', [])
            if not articles:
                break  # Stop iteration if no articles are left
            yield from articles  # Yield each article in the current batch
            offset += len(articles)
    
    def get_article_info(self, project_id, article_id):
        endpoint = f"{self.base_url}/api-json/article-info/{article_id}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {"project-id": project_id,}
        return requests.get(endpoint, headers=headers, json=body)
                   
    def upload_jsonlines(self, file_path, project_id):
        url = f"{self.base_url}/api-json/import-files/{project_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Prepare the file for upload
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.split('/')[-1], f, 'application/octet-stream')}
            # Let requests handle "Content-Type"
            response = requests.post(url, headers=headers, files=files)
        
        return response
    
    def get_article_file(self, project_id, article_id, hash):
        url = f"{self.base_url}/api-json/files/{project_id}/article/{article_id}/download/{hash}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
    