import sys
import os
project_path = os.path.dirname(os.getcwd())
sys.path.append(project_path)
import pandas as pd
from webservices import app
from webservices.models.models import MasterProjectType, db

file_path = os.path.join(os.getcwd() + "/../webservices/static/MasterProjectType.xlsx")
with app.app_context():
    db.session.query(MasterProjectType).delete()
    df = pd.read_excel(file_path)
    df = df.fillna('')
    objects = []
    for index, row in df.iterrows():
        objects.append(MasterProjectType(identifier=row['identifier'],
                                    type=row['type'],
                                    module=row['module'],
                                    state=row['state'],
                                    agent=row['agent'],
                                    sop_column=row["sop_column"],
                                    sop_delimeter=row["sop_delimeter"],
                                    special_case1=row["special_case1"] 
                                    ))
    db.session.bulk_save_objects(objects)
    db.session.commit()