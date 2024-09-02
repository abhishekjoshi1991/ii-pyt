import sys
import os
project_path = os.path.dirname(os.getcwd())
sys.path.append(project_path)
import textile
import re
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
from webservices import app
from config import SQLALCHEMY_DATABASE_URI_2
from webservices.models.models import create_engine_from_uri
from sqlalchemy import text
from webservices.models.models import SeverityLevel, db

class PopulateSeverityLevel:
    def __init__(self):
        self.level_df, self.master_redmine_df = self.get_level_df()
    
    def get_level_df(self):
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
            # get all records from redmine database
            master_redmine_df = pd.DataFrame(query_result)

            # extract records from above df having title as 'フロー' (flow, to get main page for level info)
            level_df = master_redmine_df[master_redmine_df['title'].str.contains('フロー')]
        return level_df, master_redmine_df
    
    def fetch_level_data(self):
        """
        Get level data for identifiers having seperate level pages listed in redmine database.
        Load level wise flow, description and level wise content in database
        """
        objects = []
        for i, data in self.level_df.iterrows():
            html_content = textile.textile(data['text'])
            table_pattern = re.compile(r'<table>.*?</table>', re.DOTALL)
            tables = re.findall(table_pattern, html_content)
            if tables:
                for table in tables:
                    table = table.replace('\t', '')
                    table = table.replace('<br />', '、')
                    table = table.replace('\n', '、')
                    soup = BeautifulSoup(table, 'html.parser')
                    df = pd.read_html(StringIO(str(soup)))[0]
                    rename_mapping = {col: col.lstrip('._') for col in df.columns if isinstance(col, str)}
                    df = df.rename(columns=rename_mapping)
                    df[df.columns[0]] = df[df.columns[0]].apply(self.get_level_text_using_re)

                    if any('レベル' in col for col in df.columns):
                        for index, row_data in df.iterrows():
                            level_content = self.master_redmine_df[(self.master_redmine_df['identifier'] == data['identifier']) & (self.master_redmine_df['title'] == row_data[df.columns[0]])]
                            if not level_content.empty:
                                level_content_text = level_content.iloc[0]['text']
                            else:
                                level_content_text = ''
                            objects.append(SeverityLevel(identifier=data['identifier'],
                                troubleshoot_level=row_data[df.columns[0]],
                                troubleshoot_flow=row_data[df.columns[1]],
                                troubleshoot_descripton=row_data[df.columns[2]],
                                level_content=level_content_text
                                ))
                    else:
                        pass

        identifier_list = list(map(lambda x: x.identifier, objects))
        balance_records_df = self.master_redmine_df[~self.master_redmine_df['identifier'].isin(identifier_list)]
        balance_records_df = balance_records_df[balance_records_df['title'].str.contains('障害対応手順')]
        db.session.bulk_save_objects(objects)
        db.session.commit()
        return balance_records_df

    def get_level_text_using_re(self, text):
        colon_match = re.search(r':(.*?)]', text)
        bracket_match = re.search(r'\[\[(.*?)\]\]', text)
        if colon_match:
            return colon_match.group(1)
        elif bracket_match:
            return bracket_match.group(1)
        else:
            return text
    
    def find_target_p(self, soup):
        """
        Find the first <p> tag containing the text '対応レベル' in its content or children.
        """
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            if '対応レベル' in p.get_text():
                return p
    
    def get_remaining_identifier_level_data(self, df):
        """
        Get level data for identifiers having no seperate level pages listed in redmine database, level information
        for such identifiers included in troubleshooting procedure itself
        """
        objects = []
        for i, data in df.iterrows():
            splitted_lines = data['text'].splitlines()
            text_content = ''
            for textline in splitted_lines:
                text_content = text_content + textline.strip(' ') + '\n'

            html_content = textile.textile(text_content)
            soup = BeautifulSoup(html_content, 'html.parser')
            target_p = self.find_target_p(soup)

            if target_p:
                # Find the next <ul> element after the target <p>
                target_ul = target_p.find_next('ul')

                # Extract level and respective content
                if target_ul and target_ul.get_text(strip=True):
                    top_level_items = target_ul.find_all('li', recursive=False)
                    for item in top_level_items:
                        level = item.contents[0].strip()
                        content = item.find('ul').li.text.strip()
                        objects.append(SeverityLevel(identifier=data['identifier'],
                                    troubleshoot_level=level,
                                    level_content=content
                                    ))
                else:
                    target_table = target_p.find_next('table')
                    if target_table:
                        table_df = pd.read_html(StringIO(str(soup)))[0]
                        rename_mapping = {col: col.lstrip('._') for col in table_df.columns if isinstance(col, str)}
                        table_df = table_df.rename(columns=rename_mapping)
                        table_df[table_df.columns[0]] = table_df[table_df.columns[0]].apply(self.get_level_text_using_re)
                        if any('レベル' in col for col in table_df.columns):
                            for index, row_data in table_df.iterrows():
                                level_content = self.master_redmine_df[(self.master_redmine_df['identifier'] == data['identifier']) & (self.master_redmine_df['title'] == row_data[table_df.columns[0]])]
                                if not level_content.empty:
                                    level_content_text = level_content.iloc[0]['text']
                                else:
                                    level_content_text = None
                                objects.append(SeverityLevel(identifier=data['identifier'],
                                    troubleshoot_level=row_data[table_df.columns[0]],
                                    troubleshoot_flow=row_data[table_df.columns[1]],
                                    troubleshoot_descripton=row_data[table_df.columns[2]],
                                    level_content=level_content_text
                                    ))
            else:
                table_pattern = re.compile(r'<table>.*?</table>', re.DOTALL)
                tables = re.findall(table_pattern, html_content)
                if tables:
                    for table in tables:
                        table = table.replace('\t', '')
                        soup = BeautifulSoup(table, 'html.parser')
                        grab_df = pd.read_html(StringIO(str(soup)))[0]
                        numeric_columns = pd.to_numeric(grab_df.columns, errors='coerce').notna()
                        if any(numeric_columns) and len(grab_df.columns) == 2:
                            for indx, df_row_data in grab_df.iterrows():
                                if '対応レベル' in df_row_data[0]:
                                    continue
                                else:
                                    objects.append(SeverityLevel(identifier=data['identifier'],
                                    troubleshoot_level=df_row_data[0],
                                    troubleshoot_flow=df_row_data[1],
                                    ))
                            break
        db.session.bulk_save_objects(objects)
        db.session.commit()
        
    def main(self):
        with app.app_context():
            db.session.query(SeverityLevel).delete()
            balance_df = self.fetch_level_data()
            self.get_remaining_identifier_level_data(balance_df)

obj = PopulateSeverityLevel()
obj.main()