import urllib,pickle

# TODO flesh this out way more. right now only works for gene_model
def getModel(model_id):
	if(model_id == "gene_ner"):
		url = "https://s3.amazonaws.com/sysrev-model/gene_model.pickle"
		return pickle.loads(urllib.urlopen(url).read())
	else: 
		raise ValueError("nonexistent model: {}".format(model_id))