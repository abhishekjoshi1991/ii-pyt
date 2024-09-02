import sys
import os
project_path = os.path.dirname(os.getcwd())
sys.path.append(project_path)
import re
import pandas as pd
from webservices import app
from config import SQLALCHEMY_DATABASE_URI_2
from webservices.models.models import create_engine_from_uri
from sqlalchemy import text
from webservices.models.models import ContactInformation, db


class PopulateContactInfo:
    def __init__(self):
        self.master_redmine_df, self.contact_df = self.get_contact_df()
    
    def get_contact_df(self):
        engine = create_engine_from_uri(SQLALCHEMY_DATABASE_URI_2)
        with engine.connect() as connection:
            query = """
                    SELECT wp.id as pageid, p.id as projectid, wiki_id, title, identifier, text
                    FROM redmine.wiki_pages wp
                    join redmine.projects p on p.id = wp.wiki_id 
                    join redmine.wiki_contents wc on wc.page_id = wp.id 
                    where identifier not in ('ohata-print-op', 'ohata-print-inner', 'honekawa-gouda-op', 'honekawa-gouda-inner');
                    """
            query_result = connection.execute(text(query)).fetchall()
            master_redmine_df = pd.DataFrame(query_result)
            
            # get all records related to contact information from redmine database
            contact_df = master_redmine_df[master_redmine_df['title'].str.contains('連絡先')]
        return master_redmine_df, contact_df

    def fetch_contact_data(self):
        """
        Get contact data from redmine database and also include wiki content wherever include section is present.
        """
        df = self.contact_df.sort_values(by='pageid')
        objects = []
        for index, data in df.iterrows():
            current_tuple = (data['identifier'], 1) 
            if current_tuple in [(x['identifier'], x['is_include']) for x in objects]:
                continue
            pattern = r'{{include\((.*?)\)}}'
            contact_content = data['text']
            is_include = None

            while True:
                matches = re.finditer(pattern, contact_content)
                match_list = [match for match in matches]
                if not match_list:
                    if is_include == 1:
                        break
                    else:
                        is_include = 0
                        break
                else:
                    for record in match_list:
                        include_text = record.group(1).split(':')[-1]
                        include_identifier = record.group(1).split(':')[0] if len(record.group(1).split(':')) > 1 else ''
                        if include_identifier:
                            filt_df = self.master_redmine_df[
                                (self.master_redmine_df['identifier'].str.lower()==include_identifier.lower()) & 
                                (
                                    (self.master_redmine_df['title'].str.lower()==include_text.lower()) | 
                                    (self.master_redmine_df['title'] == include_text.strip().replace(' ', '_'))
                                )
                                ]
                        else:
                            filt_df = self.master_redmine_df[
                            (
                                (self.master_redmine_df['title'].str.lower()==include_text.lower()) | 
                                (self.master_redmine_df['title'] == include_text.strip().replace(' ', '_'))
                            )
                            ]
                        if not filt_df.empty:
                            contact_content = contact_content.replace(record.group(0), filt_df.iloc[0]['text'])
                    is_include = 1
            preprocessed_contact_content = self.process_link(contact_content)
            existing_object = next((x for x in objects if x['identifier'] == data['identifier'] and x['is_include'] == 1), None)
            if not existing_object:
                objects.append({
                        'identifier': data['identifier'],
                        'contact_page_content': preprocessed_contact_content,
                        'is_include': is_include
                    })
        objects =[obj for obj in objects if obj['is_include'] != 0]
        [obj_data.pop('is_include', None) for obj_data in objects]
        db_objects = [ContactInformation(**obj_data) for obj_data in objects]

        db.session.bulk_save_objects(db_objects)
        db.session.commit()

    def process_link(self, text):
        pattern_text_in_bracket = r'\[\[(.*?)\]\]'
        match = re.finditer(pattern_text_in_bracket, text, re.DOTALL)
        match_list = [mat for mat in match]
        if match_list:
                pattern_after_colon = r':(.*?)\]\]'
                pattern_pipe = r'\[\[(.*?)\|'
                pattern_colon_pipe = r':(.*?)\|'
                pattern_text_between_bracket = r'\[\[(.*?)\]\]'
                for match_record in match_list:
                        match_pattern_colon_pipe = re.search(pattern_colon_pipe, match_record.group(0))
                        match_pattern_after_colon = re.search(pattern_after_colon, match_record.group(0))
                        match_pattern_pipe = re.search(pattern_pipe, match_record.group(0))
                        match_pattern_between_bracket = re.search(pattern_text_between_bracket, match_record.group(0))
                        if match_pattern_colon_pipe:
                                extracted_title = match_pattern_colon_pipe.group(1)
                                text_to_replace = match_record.group(0)
                                index = text.find(text_to_replace)
                                text = text[:index] + extracted_title + text[index + len(text_to_replace):]
                        elif match_pattern_after_colon:
                                extracted_title = match_pattern_after_colon.group(1)
                                text_to_replace = match_record.group(0)
                                index = text.find(text_to_replace)
                                text = text[:index] + extracted_title + text[index + len(text_to_replace):]
                        elif match_pattern_pipe:
                                extracted_title = match_pattern_pipe.group(1)
                                text_to_replace = match_record.group(0)
                                index = text.find(text_to_replace)
                                text = text[:index] + extracted_title + text[index + len(text_to_replace):] 
                        elif match_pattern_between_bracket:
                                extracted_title = match_pattern_between_bracket.group(1)
                                text_to_replace = match_record.group(0)
                                index = text.find(text_to_replace)
                                text = text[:index] + extracted_title + text[index + len(text_to_replace):] 
        return text
        
    def main(self):
        with app.app_context():
            db.session.query(ContactInformation).delete()
            self.fetch_contact_data()

obj = PopulateContactInfo()
obj.main()