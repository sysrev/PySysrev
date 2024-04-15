import requests, sqlite3, pathlib, pandas as pd, json, tqdm

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

class Synchronizer:
    
    def create_sqlite_db():
        pathlib.Path(".sr").mkdir(exist_ok=True)
        conn = sqlite3.connect('.sr/sr.sqlite')
        c = conn.cursor()

        # Create article_data table first
        c.execute('''
            CREATE TABLE IF NOT EXISTS article_data (
                primary_title TEXT,
                consensus INTEGER,
                article_id TEXT PRIMARY KEY,
                updated_time TEXT,
                notes TEXT,
                resolve INTEGER
            );
        ''')

        # Create labels table
        c.execute('''
            CREATE TABLE IF NOT EXISTS labels (
                label_id INTEGER PRIMARY KEY,
                label_id_local TEXT,
                category TEXT,
                definition TEXT,
                name TEXT,
                consensus INTEGER,
                question TEXT,
                project_ordering INTEGER,
                short_label TEXT,
                label_id_global TEXT,
                root_label_id_local TEXT,
                global_label_id TEXT,
                project_id INTEGER,
                enabled INTEGER,
                value_type TEXT,
                required INTEGER,
                owner_project_id INTEGER
            );
        ''')

        # Create article_label table with foreign key references to both labels and article_data
        c.execute('''
            CREATE TABLE IF NOT EXISTS article_label (
                article_id TEXT,
                label_id INTEGER,
                user_id INTEGER,
                answer TEXT,
                inclusion INTEGER,
                updated_time TEXT,
                confirm_time TEXT,
                resolve INTEGER,
                PRIMARY KEY (article_id, label_id),
                FOREIGN KEY (label_id) REFERENCES labels (label_id),
                FOREIGN KEY (article_id) REFERENCES article_data (article_id)
            );
        ''')

        # Indexes for improved query performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_labels_project_id ON labels (project_id);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_article_label_user_id ON article_label (user_id);')

        # Commit changes and close connection
        conn.commit()
        conn.close()

    def sync(self, client, project_id):
        project_info = client.get_project_info(project_id)
        
        labels = client.get_labels(project_id)
        labels_df = pd.DataFrame(labels)
        labels_df['definition'] = labels_df['definition'].apply(json.dumps)
        
        n_articles = project_info['result']['project']['stats']['articles']
        articles = [resp for resp in tqdm.tqdm(client.fetch_all_articles(project_id), total=n_articles)]
        
        article_labels = [a['labels'] for a in articles if a['labels'] is not None]
        article_labels = [lbl for lbls in article_labels for lbl in lbls]
        article_label_df = pd.DataFrame(article_labels)
        
        article_data = [{k: v for k, v in a.items() if k != 'labels'} for a in articles]
        article_data_df = pd.DataFrame(article_data)
        article_data_df['resolve'] = article_data_df['resolve'].apply(json.dumps)
        
        # write everything to .sr/sr.sqlite
        conn = sqlite3.connect('.sr/sr.sqlite')
        
        # Writing data to tables
        labels_df.to_sql('labels', conn, if_exists='replace', index=False)
        article_label_df.to_sql('article_label', conn, if_exists='replace', index=False)
        article_data_df.to_sql('article_data', conn, if_exists='replace', index=False)
        
        conn.close()
class Client():
    
    def __init__(self, api_key, base_url="https://www.sysrev.com"):
        self.api_key = api_key
        self.base_url = base_url
        
    def sync(self, project_id):
        Synchronizer().sync(self, project_id)
    
    def get_project_info(self, project_id):
        endpoint = f"{self.base_url}/api-json/project-info"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(endpoint, headers=headers, params={"project-id": project_id})
        return response.json()
    
    def get_labels(self, project_id):
        raw_labels = self.get_project_info(project_id)['result']['project']['labels']
        labels = [{"label_id": label_id} | raw_labels[label_id] for label_id in raw_labels.keys()]
        return labels
    
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
    