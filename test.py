import PySysrev

art = PySysrev.getEntity('pubmed',100)
print(art)

nlp = PySysrev.getModel("gene_ner")

nlp(unicode("my favorite genes are p53 and mdm2"))
