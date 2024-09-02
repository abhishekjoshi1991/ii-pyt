import sys
import os
project_path = os.path.dirname(os.getcwd())
sys.path.append(project_path)
import re
import textile
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import text
from io import StringIO
from database import get_db_engine, get_db_engine_2


class GetParentChildData():
    def __init__(self):
        self.redmine_engine = get_db_engine_2()
        self.imai_engine = get_db_engine()

    def child_parent_df(self):
        with self.redmine_engine.connect() as connection:
            child_records_query = """
                    select wp.id, title, text, identifier, wp.parent_id from wiki_pages wp
                    left join wiki_contents on wp.id = wiki_contents.page_id
                    left join wikis on wp.wiki_id = wikis.id
                    left join projects on wikis.project_id = projects.id
                    WHERE wp.id NOT IN (SELECT parent_id FROM wiki_pages WHERE parent_id IS NOT NULL) and wp.parent_id IS NOT NULL
                    and identifier not in ('ohata-print-op', 'ohata-print-inner', 'honekawa-gouda-op', 'honekawa-gouda-inner');
                    """
    
            parent_records_query = """
                    SELECT wp.id, title, text
                    FROM redmine.wiki_pages as wp
                    left join wiki_contents on wp.id = wiki_contents.page_id
                    WHERE wp.id NOT IN (SELECT id
                    FROM redmine.wiki_pages
                    WHERE id NOT IN (SELECT parent_id FROM redmine.wiki_pages WHERE parent_id IS NOT NULL) and wp.parent_id IS NOT NULL);
                    """
            query_result_child = connection.execute(text(child_records_query)).fetchall()
            child_df = pd.DataFrame(query_result_child)

            query_result_parent = connection.execute(text(parent_records_query)).fetchall()
            parent_df = pd.DataFrame(query_result_parent)
            return child_df, parent_df
    
    def get_module_state_agent(self):
        child_df, parent_df = self.child_parent_df()
        child_df['module'] = ''
        child_df['state'] = ''
        child_df['agent'] = ''
        child_df['level'] = ''
        child_df['level_content'] = ''
        for i, data in child_df.iterrows():
            parent_id = data['parent_id']
            parent_record = parent_df[parent_df['id']==parent_id]['text']
            child_title = data['title']
            identifier = data['identifier']
            response = self.extract_tables(parent_record, child_title, identifier)
            if response:
                filtered_df = child_df[(child_df['identifier'] == identifier) & (child_df['title'] == response.get('severity_level'))]
                level_content = ''
                if len(filtered_df) == 1:
                    level_content = filtered_df.iloc[0]['text']

                mask = child_df['id'] == data['id']
                module = response.get('モジュール') or response.get('モジュール名') or response.get('監視項目')
                pattern_module = r'\[\[(.*?)\]\]'
                module_data = re.findall(pattern_module, module)
                module_values = []
                if module_data:
                    for mod_val in module_data:
                        module_values.append(mod_val.split(':', 2)[-1])
                    module = '、'.join(module_values)
                state_from_response = response.get('状態') or response.get('障害箇所')
                if state_from_response:
                    pattern = r':(.*?)\]\]'
                    match = re.search(pattern, state_from_response)
                    if match:
                        state = match.group(1)
                    else:
                        pattern = r'\[\[(.*?)\]\]'
                        match = re.search(pattern, state_from_response)
                        if match:
                            state = match.group(1)
                        else:
                            state = state_from_response
                else:
                    state = state_from_response
                agent = response.get('エージェント') or response.get('対象エージェント') or response.get('対象サーバ')
                agent = '*' if agent == '、' else agent
                severity_level = response.get('severity_level')
                # columns_to_update = ['module', 'state', 'agent']
                columns_to_update = ['module', 'state', 'agent', 'level', 'level_content']
                child_df.loc[mask, columns_to_update] = [str(module.strip(',')).replace('、、', '、') if module else '', str(state.strip(',')).replace('、、', '、') if state else '', str(agent.strip(',')).replace('、、', '、') if agent else '', severity_level, level_content]
        df_with_mod_state_agent = child_df[child_df['module'].notna() & (child_df['module'] != '')]
        return df_with_mod_state_agent

    def extract_tables(self, textile_content, title, identifier):
        all_content = textile_content.iloc[0]
        if '<DISK>' in all_content:
            all_content = all_content.replace('<DISK>', '--disk--')
        
        # to remove extra whitespace (if any) from the wiki content
        splitted_lines = all_content.splitlines()
        content = ''
        for textline in splitted_lines:
            content = content + textline.strip(' ') + '\n'
            
        # pattern to match rowspan like /3.
        pattern_rowspan = r'/(\d+)\.'
        match_for_rowspan = re.finditer(pattern_rowspan,content)
        match_for_rowspan_list = [mat for mat in match_for_rowspan]
        match_dict = {match.group(0): match for match in match_for_rowspan_list}.values()
        match_for_rowspan_unique = list(match_dict)
        
        if match_for_rowspan_unique:
            for each_match in match_for_rowspan_unique:
                text_to_replace = each_match.group(0)
                content = content.replace(text_to_replace, text_to_replace+' ')
        
        matches = re.findall(r'\[\[(?:(?!\[\[).)*?\]\]', content, flags=re.DOTALL)
        if matches:
            for item in matches:
                content = content.replace(item, item.replace('|', ':'))
        
        html_content = textile.textile(content)
        table_pattern = re.compile(r'<table>.*?</table>', re.DOTALL)
        tables = re.findall(table_pattern, html_content)
        
        # remove _,(), whitespaces from title and make it lowercase
        pattern = r'[ _()]'
        title_new = re.sub(pattern, '', title).lower()

        if tables:
            result_dict = {}
            with self.imai_engine.connect() as connection:
                sql_query = text(f"SELECT * FROM master_project_type WHERE identifier = '{identifier}'")
                query_result = connection.execute(sql_query)
                identifier_match_records = query_result.first()
                if identifier_match_records:
                    columns_to_check = [identifier_match_records[3], identifier_match_records[4], identifier_match_records[5]]
                    sop_column = identifier_match_records[6]
                    sop_delimeter_pattern = identifier_match_records[7]
                    # new two lines below
                    special_case1 = identifier_match_records[8]
                    level_column = identifier_match_records[-1]
                    for table in tables:
                        table = table.replace('\t', '')
                        table = table.replace('<br />', '、')
                        table = table.replace('\n', '、')
                        soup = BeautifulSoup(table, 'html.parser')
                        df = pd.read_html(StringIO(str(soup)))[0]
                        rename_mapping = {col: col.lstrip('._') for col in df.columns if isinstance(col, str)}
                        df = df.rename(columns=rename_mapping)
                        pattern_text_between_bracket = r'\[\[(.*?)\]\]' # to get text in between [[]]
                        pattern_for_two_colon = r'\[\[.*?:.*?:.*?\]\]'
                        
                        columns_to_check = [item for item in columns_to_check if item.strip() != ""]
                        if len(columns_to_check) > 0:     
                            if any(col in df.columns for col in columns_to_check):
                                if (df[sop_column].str.count(pattern_text_between_bracket) > 1).any(): # condition when multiple links are present in cell under sop column 
                                    df['extracted_part'] = df[sop_column].str.findall(pattern_text_between_bracket).apply(lambda x: ', '.join(x) if isinstance(x, list) else None)
                                elif df[sop_column].str.match(pattern_for_two_colon).any(): # condition when two colons are present in wiki content
                                    df['extracted_part'] = df[sop_column].str.extract(sop_delimeter_pattern)
                                    has_two_colons = df[sop_column].str.match(pattern_for_two_colon)
                                    df.loc[has_two_colons, 'extracted_part'] = df.loc[has_two_colons, sop_column].str.split(':', n=2).str[1]
                                else:
                                    df['extracted_part'] = df[sop_column].str.extract(sop_delimeter_pattern)
                                
                                # condition to extract text in between [[]] if extracted column has NaN value
                                if df['extracted_part'].isnull().any():
                                    null_rows= df['extracted_part'].isnull()
                                    df.loc[null_rows, 'extracted_part'] = df[sop_column].str.extract(pattern_text_between_bracket).squeeze()
                                df['cleaned_extracted_part'] = df['extracted_part'].str.replace(r'[ _().]', '', regex=True)
                                
                                if special_case1 == title:
                                    if any(df.stack().astype(str).str.contains('—disk—')):
                                        df.replace(r'—disk—', '<disk>', regex=True, inplace=True)
                                        df['cleaned_extracted_part'] = df['extracted_part'].str.replace(r'[ _()/]', '', regex=True)

                                        title = title.replace('&lt', '<')
                                        title = title.replace('&gt', '>')
                                        title_new = re.sub(r'[_()/]', '', title)
                                        title_new = title_new.lower()
                                    
                                df['cleaned_extracted_part'] = df['cleaned_extracted_part'].str.lower()
                            
                                if (df['cleaned_extracted_part'].str.contains(title_new)).any():
                                    if len(df[df['cleaned_extracted_part'].str.contains(title_new, na=False)]) > 1:
                                        # get exact match
                                        if df['cleaned_extracted_part'].nunique() == 1: # if df contains only unique values
                                            df = df.apply(lambda column: '、'.join(map(str, pd.unique(column))) if ',' not in column.iloc[0] else  ' '.join(map(str, pd.unique(column))), axis=0)
                                            extracted_information =  df.to_dict()
                                            result_dict.update({key: result_dict[key] + '、' + extracted_information[key] if key in result_dict and extracted_information[key] not in result_dict[key] else extracted_information[key] for key in extracted_information.keys()})
                                        else:
                                            filt_df = df[df['cleaned_extracted_part'] == title_new]
                                            if not filt_df.empty:
                                                if filt_df['cleaned_extracted_part'].nunique() == 1: # if df contains unique and other values
                                                    filt_df = filt_df.apply(lambda column: '、'.join(map(str, pd.unique(column.dropna()))) if ',' not in str(column.iloc[0]) else ' '.join(map(str, pd.unique(column.dropna()))) if pd.notna(column.iloc[0]) else '', axis=0)
                                                    extracted_information = filt_df.to_dict()
                                                    result_dict.update({key: result_dict[key] + '、' + extracted_information[key] if key in result_dict and extracted_information[key] not in result_dict[key] else extracted_information[key] for key in extracted_information.keys()})
                                                else:
                                                    extracted_information = filt_df.iloc[0].to_dict()
                                                    result_dict.update({key: result_dict[key] + '、' + extracted_information[key] if key in result_dict and extracted_information[key] not in result_dict[key] else extracted_information[key] for key in extracted_information.keys()})
                                    else:
                                        # this condition is used to find exact match, for sop column like プロセス数, プロセス数_java, プロセス数_james. 
                                        filt_df = df[df['cleaned_extracted_part'] == title_new]
                                        if not filt_df.empty:
                                            extracted_information = filt_df.iloc[0].to_dict()
                                            result_dict.update({key: result_dict[key] + '、' + extracted_information[key] if key in result_dict and extracted_information[key] not in result_dict[key] else extracted_information[key] for key in extracted_information.keys()})
                                        else:
                                            # below if condition for project with sop column contains multiple [[..]], [[..]] as a single value
                                            if (df[sop_column].str.count(pattern_text_between_bracket) > 1).any():
                                                extracted_information = df[df['cleaned_extracted_part'].str.contains(title_new, na=False)].iloc[0].to_dict()
                                                result_dict.update({key: result_dict[key] + '、' + extracted_information[key] if key in result_dict and extracted_information[key] not in result_dict[key] else extracted_information[key] for key in extracted_information.keys()})
                                elif all(col in df.columns for col in columns_to_check) and special_case1: # <DISK> for kitasanriku-sodegahama-gyokyo-op
                                    filt_df = df[df['cleaned_extracted_part'] == title_new]
                                    if not filt_df.empty:
                                        extracted_information = filt_df.iloc[0].to_dict()
                                        result_dict.update({key: result_dict[key] + '、' + extracted_information[key] if key in result_dict and extracted_information[key] not in result_dict[key] else extracted_information[key] for key in extracted_information.keys()})
                                else:
                                    pass
                    if result_dict:
                        try:
                            result_dict_level_col =  result_dict.get(level_column)
                            if result_dict_level_col:
                                level_match_1 = re.search(r':(.*?)]', result_dict_level_col)
                                level_match_2 = re.search(pattern_text_between_bracket, result_dict_level_col)
                                if level_match_1:
                                    level = level_match_1.group(1) 
                                elif level_match_2:
                                    level = level_match_2.group(1) 
                                else:
                                    level = result_dict_level_col
                                result_dict.update({'severity_level': level})
                        except Exception as e:
                            pass
                    return result_dict