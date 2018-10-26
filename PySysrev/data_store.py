from cassandra.cluster import Cluster
import pandas as pd

# TODO flesh this out way more. right now only works for pubmed
def getEntity(resource,id):
	return getEntities(resource,[id])

def getEntities(resource,ids):
	if resource == 'pubmed':
	    cluster = Cluster()
	    session = cluster.connect('biosource')
	    idString = ",".join(str(i) for i in ids)
	    query = 'SELECT * FROM pubmed WHERE pmid in ({})'.format(idString)
	    df = pd.DataFrame(list(session.execute(query)))
	    # print(df)
	    return df
	else:
		raise ValueError("no resource named {}".format(resource))