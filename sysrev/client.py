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
    
    def create_sqlite_db(self):
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

    # TODO - this could be made more efficient by checking sqlite state and updating the sysrev api
    def sync(self, client, project_id):
        
        if not pathlib.Path('.sr/sr.sqlite').exists():
            self.create_sqlite_db()
            
        project_info = client.get_project_info(project_id)
        
        labels = client.get_labels(project_id)
        labels_df = pd.DataFrame(labels)
        labels_df['definition'] = labels_df['definition'].apply(json.dumps)
        
        n_articles = project_info['result']['project']['stats']['articles']
        articles = [resp for resp in tqdm.tqdm(client.fetch_all_articles(project_id), total=n_articles)]
        
        article_labels = [a['labels'] for a in articles if a['labels'] is not None]
        article_labels = [lbl for lbls in article_labels for lbl in lbls]
        article_label_df = pd.DataFrame(article_labels)
        article_label_df['answer'] = article_label_df['answer'].apply(json.dumps)
        
        article_data = [{k: v for k, v in a.items() if k != 'labels'} for a in articles]
        article_data_df = pd.DataFrame(article_data)
        article_data_df['notes'] = article_data_df['notes'].apply(json.dumps)
        article_data_df['resolve'] = article_data_df['resolve'].apply(json.dumps)
            
        article_info = []
        for article_id in tqdm.tqdm(article_data_df['article-id'], total=n_articles):
            article_info.append(client.get_article_info(project_id, article_id))
        
        full_texts = pd.DataFrame([{**ft} for a in article_info for ft in a['article'].get('full-texts', []) ])
        full_texts.columns = [col.split('/')[-1] for col in full_texts.columns]
        
        auto_labels = pd.DataFrame([
            {**{'article-id': a['article'].get('article-id'), 'label-id': label_id}, **details} for a in article_info
            for label_id, details in a['article'].get('auto-labels', {}).items() ])
        auto_labels['answer'] = auto_labels['answer'].apply(json.dumps)
        
        csl_citations = pd.DataFrame([
            {**{k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in item['itemData'].items()}, 
             'article-id': a['article'].get('article-id')} 
            for a in article_info for item in a['article'].get('csl-citation', {}).get('citationItems', [])])
        csl_citations['issued'] = csl_citations['issued'].apply(json.dumps)
        csl_citations['author'] = csl_citations['author'].apply(json.dumps)
        
        # write everything to .sr/sr.sqlite
        conn = sqlite3.connect('.sr/sr.sqlite')
        
        def write_df(df,name):
            # replace any - with _ in column names and remove duplicates
            df.columns = df.columns.str.replace('-', '_')
            df = df.loc[:,~df.columns.duplicated()]
            df.to_sql(name, conn, if_exists='replace', index=False) if not df.empty else None
                
                
        # Writing data to tables
        write_df(labels_df,'labels')
        write_df(article_label_df,'article_label')
        write_df(article_data_df,'article_data')
        write_df(full_texts,'full_texts')
        write_df(auto_labels,'auto_labels')
        write_df(csl_citations,'csl_citations')
        
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
        response = requests.get(endpoint, headers=headers, json=body)
        return response.json()['result']
                   
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
    