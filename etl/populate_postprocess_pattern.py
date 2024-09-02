import sys
import os
project_path = os.path.dirname(os.getcwd())
sys.path.append(project_path)
import pandas as pd
from webservices import app
from webservices.models.models import PostprocessPattern, db

file_path = os.path.join(os.getcwd() + "/../webservices/static/PostProcessPatterns.xlsx")
with app.app_context():
    db.session.query(PostprocessPattern).delete()
    df = pd.read_excel(file_path)
    df = df.fillna('')
    objects = []
    for index, row in df.iterrows():
        objects.append(PostprocessPattern(pattern=row['pattern'],
                                    replacement=row['replacement'],
                                    description=row['description']
                                    ))
    db.session.bulk_save_objects(objects)
    db.session.commit()