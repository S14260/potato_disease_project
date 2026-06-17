from knowledge.pesticide_db import pesticide_db

def retrieve_pesticide(disease_key):

    return pesticide_db.get(disease_key, [])