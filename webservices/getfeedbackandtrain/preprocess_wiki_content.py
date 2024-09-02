import os
import re
import datetime
import pandas as pd
from sqlalchemy import text
from database import get_db_engine_2
from get_feedback_data import GetFeedbackData

feedback_data_obj = GetFeedbackData()

class PrepareModelDataset():
        def __init__(self):
                self.engine = get_db_engine_2()
                self.include_df = self.data_for_include_section()

        def data_for_include_section(self):
                with self.engine.connect() as connection:
                        include_records_query = """
                                SELECT wp.id, identifier, title, text FROM wiki_pages wp
                                left join wiki_contents on wp.id = wiki_contents.page_id
                                left join wikis on wp.wiki_id = wikis.id
                                left join projects on wikis.project_id = projects.id
                        """

                        include_records = connection.execute(text(include_records_query)).fetchall()
                        include_df = pd.DataFrame(include_records)
                return include_df
        
        def generate_question(self, row):
                questions = [
                        f"識別子が「{row['identifier']}」、モジュールが「{row['module']}」、エージェントが「{row['agent']}」、障害状態が「{row['state']}」の場合、対応手順はどうなるでしょうか？",
                        f"識別子「{row['identifier']}」、モジュール「{row['module']}」、エージェント「{row['agent']}」、障害状態「{row['state']}」の場合に行う対応手順は何ですか?",
                        f"識別子「{row['identifier']}」、モジュール「{row['module']}」、エージェント「{row['agent']}」、および障害状態「{row['state']}」に基づいて発生されたシナリオの場合、標準的な対応手順は何になりますか?",
                        f"識別子が「{row['identifier']}」、モジュールが「{row['module']}」、エージェントが「{row['agent']}」、障害状態が「{row['state']}」の場合、推奨される対応手順は何ですか?"
                ]
                return questions
        
        def df_based_question_format(self, input_df):
                expanded_records = []
                for _, row in input_df.iterrows():
                        questions = self.generate_question(row)
                        for question in questions:
                                record = row.copy()
                                record['question'] = question
                                expanded_records.append(record)
                expanded_df = pd.DataFrame(expanded_records)
                return expanded_df
        
        def get_feedback_collected_data(self):
                df = feedback_data_obj.get_wiki_content()
                distinct_df = df.drop_duplicates(subset=['decoded_correct_url'])
                test_df_other_than_distinct = df.drop(distinct_df.index)
                return distinct_df, test_df_other_than_distinct
    
        # Function to include wiki content in include tag, like {{include(iwakura-op:岩倉ネジ製作所 連絡先)}}
        def add_include_section(self, text, identifier):
                text = text.replace('※', '')
                pattern = r'{{include\((.*?)\)}}'
                while True:
                        matches = re.finditer(pattern, text)
                        match_list = [match for match in matches]
                        if not match_list:
                                break
                        for record in match_list:
                                include_text = record.group(1).split(':')[-1]
                                if not '連絡先' in include_text:
                                        filt_df = self.include_df[(self.include_df['identifier'].str.lower()==identifier.lower()) & (self.include_df['title'].str.lower()==include_text.lower())]
                                        if not filt_df.empty:
                                                include_text_content = filt_df.iloc[0]['text']
                                                text = text.replace(record.group(0), include_text_content)
                                        else:
                                                text = text.replace(record.group(0), '')
                                else:
                                        text = text.replace(record.group(0), '')
                return text

        # Function to get only wiki title text from text like [[iwakura-op:インターネット経由ping疎通]], only if text is under header tag
        def get_wiki_title(self, text):
                pattern_header_with_title = re.compile(r'h[1-6]\.\s*(.*?)\n', re.DOTALL)
                match = re.finditer(pattern_header_with_title, text)
                pattern_after_colon = r':(.*?)\]\]'
                pattern_before_colon = r'\[\[(.*?):'
                pattern_colon_pipe = r':(.*?)\|'
                pattern_text_between_bracket = r'\[\[(.*?)\]\]'
                is_match = [mat for mat in match]
                if is_match:
                        count = 0
                        for match_record in is_match:
                                # get match for pattern colon, on text indexed on start and end text 
                                match_pattern_colon_pipe = re.search(pattern_colon_pipe, match_record.group(0))
                                match_pattern_after_colon = re.search(pattern_after_colon, match_record.group(0))
                                match_pattern_before_colon = re.search(pattern_before_colon, match_record.group(0))
                                match_pattern_between_bracket = re.search(pattern_text_between_bracket, match_record.group(0))
                                if match_pattern_colon_pipe:
                                        extracted_title = match_pattern_colon_pipe.group(1) if count == 0 else match_pattern_colon_pipe.group(1)
                                        text_to_replace = match_record.group(1)
                                        index = text.find(text_to_replace)
                                        text = text[:index] + extracted_title + text[index + len(text_to_replace):]
                                elif match_pattern_after_colon:
                                        extracted_title = match_pattern_after_colon.group(1) if count == 0 else match_pattern_after_colon.group(1)
                                        text_to_replace = match_record.group(1)
                                        index = text.find(text_to_replace)
                                        text = text[:index] + extracted_title + text[index + len(text_to_replace):]
                                elif match_pattern_before_colon:
                                        extracted_title = match_pattern_before_colon.group(1) if count == 0 else match_pattern_before_colon.group(1)
                                        text_to_replace = match_record.group(1)
                                        index = text.find(text_to_replace)
                                        text = text[:index] + extracted_title + text[index + len(text_to_replace):]
                                elif match_pattern_between_bracket:
                                        extracted_title = match_pattern_between_bracket.group(1) if count == 0 else match_pattern_between_bracket.group(1)
                                        text_to_replace = match_record.group(1)
                                        index = text.find(text_to_replace)
                                        text = text[:index] + extracted_title + text[index + len(text_to_replace):]
                                else:
                                        if count == 0:
                                                first_record = match_record.group(0)
                                                match_first_record_heading = re.search(pattern_header_with_title, first_record)
                                                if match_first_record_heading:
                                                        if '概要' not in first_record:
                                                                text_to_replace = match_first_record_heading.group(1)
                                                                extracted_title = match_first_record_heading.group(1)
                                                                index = text.find(text_to_replace)
                                                                text = text[:index] + extracted_title + text[index + len(text_to_replace):]
                                        else:
                                                count = count + 1
                                                continue
                                count = count + 1
                        return text
                else:
                        return text

        # Function to remove <pre>... </pre> tags from wiki_content
        def remove_pre_tag(self, text):
                pattern = r'<pre>(.*?)</pre>'
                matches = re.finditer(pattern, text, re.DOTALL) # get matches for pre tag
                match_list = [match for match in matches]
                if match_list:
                        for record in match_list:
                                text_inside_pre = record.group(1)
                                pattern_command_master = r'\$(.*?)(?:\n|$)'
                                pattern_command_hash= r'\#(.*?)(?:\n|$)'
                                pattern_command_master_match = re.findall(pattern_command_master, text_inside_pre) # get matches for command starts with $
                                pattern_command_hash_master_match = re.findall(pattern_command_hash, text_inside_pre) # get matches for command starts with $
                                if pattern_command_master_match or pattern_command_hash_master_match:
                                        lines = [rec_line for rec_line in text_inside_pre.split('\n') if rec_line.strip()]
                                        flag_output = False
                                        for i, line in enumerate(lines):
                                                pattern_command_match = re.search(pattern_command_master, line)
                                                hash_match = re.search(pattern_command_hash, line)
                                                if hash_match:
                                                        lines[i] = '次のコマンドを実行します\n' + hash_match[1].strip()
                                                        flag_output = False
                                                elif pattern_command_match:
                                                        lines[i] = '次のコマンドを実行します\n' + pattern_command_match[1].strip()
                                                        flag_output = False
                                                else:
                                                        if not flag_output:
                                                                lines[i] = '出力例\n' + line.strip() + '。。'
                                                        else:
                                                                lines[i-1] = lines[i-1].strip('。')
                                                                lines[i] = line.strip()
                                                        flag_output = True
                                        lines.append('。。') if not lines[-1].endswith('。。') else lines
                                        replacement_text = '\n'.join(lines)
                                        text = text.replace(record.group(0), replacement_text)
                                else:
                                        lines = record.group(1).split('\n')        
                                        for i, line in enumerate(lines):
                                                lines[i] = line if line.strip() != '' else ''
                                        replacement_text = '\n'.join(lines)
                                        text = text.replace(record.group(0), replacement_text)
                return text

        def remove_warning_section(self, text):
                pattern_warning = r'{{warning(.*?)}}'
                warning_match = re.finditer(pattern_warning, text, re.DOTALL)
                warning_match_list = [match for match in warning_match]

                if warning_match_list:
                        for record in warning_match_list:
                                replacement_text = record.group(1).strip()
                                text = text.replace(record.group(0), '警告:\n' + replacement_text)
                return text

        def remove_important_section(self, text):
                pattern_important = r'{{important(.*?)}}'
                important_match = re.finditer(pattern_important, text, re.DOTALL)
                important_match_list = [match for match in important_match]

                if important_match_list:
                        for record in important_match_list:
                                replacement_text = record.group(1).strip()
                                text = text.replace(record.group(0), '重要:\n' + replacement_text)
                return text

        def remove_note_section(self, text):
                pattern_note = r'{{note(.*?)}}'
                note_match = re.finditer(pattern_note, text, re.DOTALL)
                note_match_list = [match for match in note_match]

                if note_match_list:
                        for record in note_match_list:
                                replacement_text = record.group(1).strip()
                                text = text.replace(record.group(0), '注記:\n' + replacement_text)
                return text

        def remove_collapse_section(self, text):
                pattern_collapse = r'{{collapse(.*?)}}'
                collapse_match = re.finditer(pattern_collapse, text, re.DOTALL)
                collapse_match_list = [match for match in collapse_match]

                if collapse_match_list:
                        for record in collapse_match_list:
                                replacement_text = record.group(1).strip()
                                text = text.replace(record.group(0), replacement_text)
                return text

        # Functions to remove cut_start and cut_end from wiki_content
        def replace_cut_start(self, match):
                return match.group(1)

        def cut_start_text(self, text):
                cut_start_removed_text = re.sub(r'\{\{cut_start\((.*?)\)\}\}', self.replace_cut_start, text)
                cut_end_removed_text = cut_start_removed_text.replace('{{cut_end}}', '')
                # if cut_start is present without any title, then remove that explicitly
                transformed_text = cut_end_removed_text.replace('{{cut_start}}', '')
                return transformed_text

        def process_links(self, text):
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
                                        extracted_title = '参照URL ' + match_pattern_colon_pipe.group(1) + '。。'
                                        text_to_replace = match_record.group(0)
                                        index = text.find(text_to_replace)
                                        text = text[:index] + extracted_title + text[index + len(text_to_replace):]
                                elif match_pattern_after_colon:
                                        extracted_title = '参照URL ' + match_pattern_after_colon.group(1) + '。。'
                                        text_to_replace = match_record.group(0)
                                        index = text.find(text_to_replace)
                                        text = text[:index] + extracted_title + text[index + len(text_to_replace):]
                                elif match_pattern_pipe:
                                        extracted_title = '参照URL ' + match_pattern_pipe.group(1) + '。。'
                                        text_to_replace = match_record.group(0)
                                        index = text.find(text_to_replace)
                                        text = text[:index] + extracted_title + text[index + len(text_to_replace):] 
                                elif match_pattern_between_bracket:
                                        extracted_title = '参照URL ' + match_pattern_between_bracket.group(1) + '。。'
                                        text_to_replace = match_record.group(0)
                                        index = text.find(text_to_replace)
                                        text = text[:index] + extracted_title + text[index + len(text_to_replace):] 
                return text

        def add_x0001(self, text):
                text = text.replace('\n','_x0001_')
                return text
        
        def preprocess_data(self):
                feedback_data_distinct_df, test_df = self.get_feedback_collected_data()

                # apply operations to preprocess wiki content step by step
                feedback_data_distinct_df.loc[:, 'include_section'] = feedback_data_distinct_df.apply(lambda row: self.add_include_section(row['text'], row['identifier']), axis=1)
                feedback_data_distinct_df.loc[:, 'title_extraction_from_header'] = feedback_data_distinct_df.apply(lambda row: self.get_wiki_title(row['include_section']), axis=1)
                feedback_data_distinct_df.loc[:, 'pre_removed'] = feedback_data_distinct_df.apply(lambda row: self.remove_pre_tag(row['title_extraction_from_header']), axis=1)
                feedback_data_distinct_df.loc[:, 'warning_text'] = feedback_data_distinct_df.apply(lambda row: self.remove_warning_section(row['pre_removed']), axis=1)
                feedback_data_distinct_df.loc[:, 'important_text'] = feedback_data_distinct_df.apply(lambda row: self.remove_important_section(row['warning_text']), axis=1)
                feedback_data_distinct_df.loc[:, 'note_text'] = feedback_data_distinct_df.apply(lambda row: self.remove_note_section(row['important_text']), axis=1)
                feedback_data_distinct_df.loc[:, 'collapse'] = feedback_data_distinct_df.apply(lambda row: self.remove_collapse_section(row['note_text']), axis=1)
                feedback_data_distinct_df.loc[:, 'cut_start_removed'] = feedback_data_distinct_df.apply(lambda row: self.cut_start_text(row['collapse']), axis=1)
                feedback_data_distinct_df.loc[:, 'processed_content'] = feedback_data_distinct_df.apply(lambda row: self.process_links(row['cut_start_removed']), axis=1)
                feedback_data_distinct_df.loc[:, 'final_processed_content_x0001'] = feedback_data_distinct_df.apply(lambda row: self.add_x0001(row['processed_content']), axis=1)

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                file_save_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 'webservices/static/feedback_data')

                train_df = self.df_based_question_format(feedback_data_distinct_df)
                train_df.to_excel(f'{file_save_path}/train_data_{timestamp}.xlsx')

                test_data_df = self.df_based_question_format(test_df)
                test_data_df.to_excel(f'{file_save_path}/test_data_{timestamp}.xlsx')
                return train_df
