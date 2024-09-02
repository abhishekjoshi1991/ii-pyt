import torch
import re
import textile
from sqlalchemy import text
import pandas as pd
from bs4 import BeautifulSoup
from flask import jsonify, make_response
from webservices.models.models import PostprocessPattern, db
from webservices.services import GetModelTokenizer

trained_model_class_obj = GetModelTokenizer()
model = trained_model_class_obj.load_model()
tokenizer = trained_model_class_obj.load_tokenizer()

class GenerateSOP:
    def generate_text(self, model,tokenizer, sequence, max_length):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        
        ids = tokenizer.encode(f'{sequence}', return_tensors='pt').to(device)
        final_outputs = model.generate(
            ids,
            do_sample=True,
            max_length=max_length,
            pad_token_id=model.config.eos_token_id,
            top_k=50,
            top_p=0.95,
            temperature=0.001
        )
        text = tokenizer.decode(final_outputs[0], skip_special_tokens=False)
        return text
    
    def get_query_output(self, query, customer_specific, level):
        max_len = 1000
        model_generated_text = self.generate_text(model, tokenizer, query, max_len)
        generated_text = model_generated_text.split('[SEP]')[-1].strip(' ')

        # code for replacing unicode characters and remove eos tokens
        generated_text = re.sub(r'<\|end[\s\S]*', '', generated_text)
        generated_text = generated_text.replace('_x0001_', chr(10))
        generated_text = generated_text.replace('<unk>', ' ')
        generated_text = generated_text.replace('unk>', '')

        if customer_specific:
            generated_text = self.get_customer_specific_sop(generated_text, query, level=level)

        cleaned_text = self.get_table(generated_text)
        cleaned_text = self.postprocess_textile_tags(cleaned_text)

        cleaned_text = cleaned_text.replace('。。', '')
        cleaned_text = cleaned_text.replace('\t', '')
        cleaned_text = cleaned_text.replace('</br>', '')
        cleaned_text = cleaned_text.replace("<table>", "<table class='table table-bordered'>")
        vals = {
            'query': query,
            'orignal_generated_SOP': generated_text.replace('。。', ''),
            'modified_SOP_html': cleaned_text
        }        
        return make_response(jsonify(vals), 200)
    
    def get_sop_by_parameters(self, query, customer_specific, level):
        output = self.get_query_output(query, customer_specific, level)
        return output
    
    def get_customer_specific_sop(self, generated_text, query, level):
        customer_specific_sop = ''
        identifier_match = re.search(r'識別子が「([^」]+)」', query)
        if identifier_match:
            identifier = identifier_match.group(1).split('-')[0]
        else:
            identifier = ''

        level_text, troubleshoot_flow = self.fetch_level(identifier, level)
        contact_text = self.fetch_contact_data(identifier)
        if troubleshoot_flow and level_text:
            pattern_overview_match = re.search(r'h\d\.\s*概要(.*?)h\d\.', level_text, re.DOTALL)
            if pattern_overview_match:
                level_content_to_show = pattern_overview_match.group(1)
            else:
                level_content_to_show = ''
            content_dict = {0: level_content_to_show,
                                1: '',
                                2: generated_text,
                                3: contact_text}
            pattern_procedure_match = re.search(r'h3\. 対応手順(.*?)(h\d\. |$)', level_text, re.DOTALL)
            if pattern_procedure_match:
                ordered_list_items = re.findall(r'(?m)^# (.*)', pattern_procedure_match.group(1))
                if ordered_list_items:
                    numbered_list_items = [f"{i+1}: {item.strip()}" for i, item in enumerate(ordered_list_items)]
                    for index_num, item in enumerate(numbered_list_items):
                        customer_specific_sop = f"{customer_specific_sop}{item}\n{content_dict[index_num]}\n" if index_num != 0 else f"{customer_specific_sop}h1. {level}\n{content_dict[index_num]}\n{item}\n"
                else: #considering level 3
                    customer_specific_sop = f"{customer_specific_sop}\n{pattern_procedure_match.group(0)}"
                    return customer_specific_sop
            else: #ordered list items are not present as #
                customer_specific_sop = f"{level_text}{generated_text}\n{contact_text}"
        elif troubleshoot_flow:
            content_dict = {0: level_text,
                                1: '',
                                2: generated_text,
                                3: contact_text}
            if '→' in troubleshoot_flow:
                flow_list = troubleshoot_flow.split('→')
                numbered_flow_list = [f"{i+1}: {item}" for i, item in enumerate(flow_list)]
                for index, flow in enumerate(numbered_flow_list):
                    customer_specific_sop = f"{customer_specific_sop}{flow}\n{content_dict[index]}\n" if index != 0 else f"{customer_specific_sop}h1. {level}\n{content_dict[index]}\n{flow}\n"
            else:
                customer_specific_sop = f"{level}\n{level_text}{generated_text}\n{contact_text}"
        elif not troubleshoot_flow and level_text:
            customer_specific_sop = f"{customer_specific_sop}h1. {level}\n{level_text}\n{generated_text}\n{contact_text}"
        else:
            customer_specific_sop = f"{customer_specific_sop}h1. {level}\n{level_text}\n{generated_text}\n{contact_text}"
        return customer_specific_sop

    def get_table(self, text):
        textile_text = textile.textile(text)
        textile_text = re.sub(r'(\t+)<table>', r'<table>', textile_text)
        textile_text = re.sub(r'</table>.*?(\t+)', r'</table>', textile_text)
        table_pattern = re.compile(r'<table>.*?</table>', re.DOTALL)
        tables = re.findall(table_pattern, textile_text)

        for table in tables:
            soup = BeautifulSoup(table, 'html.parser')
            td_tags = soup.find_all(['th','td'])
            new_row = ''
            new_html = ''
            if len(soup.find_all('tr')) > 1:
                first_tr_tag_length = len(soup.find('tr').find_all(recursive=False))
                tr_tags = soup.find_all('tr')
                
                for i, tr in enumerate(tr_tags, 1):
                    len_tags_inside_tr = len(tr.find_all(recursive=False))
                    if len_tags_inside_tr != first_tr_tag_length:
                        pattern = r'<td>\s*(?:<br\s*/?>\s*)*</td>'
                        replaced_empty_td = re.sub(pattern, '</tr><tr>', str(tr))
                        new_html = new_html + replaced_empty_td
                    else:
                        new_html = new_html + str(tr)
                new_html = f'<table>{new_html}</table>'
                new_html = re.sub(r'\n', '', new_html)
                new_html = re.sub(r'_\.', '', new_html)
            else:
                for td_tag in td_tags:
                    if td_tag and all(child.name == 'br' or (child.name is None and child.strip() == '') for child in td_tag.children):
                        new_row += '</tr><tr>'
                    else:
                        new_row += f'{td_tag}'
                new_html += f'<tr>{new_row}</tr>'
                new_html = f'<table>{new_html}</table>'

            index_table_start = textile_text.find(table)
            index_table_end = textile_text.find(table) + len(table)
            textile_text = textile_text.replace(textile_text[index_table_start:index_table_end], new_html)
        return textile_text

    def postprocess_textile_tags(self, cleaned_text):
        replacements = PostprocessPattern.query.all()
        for rplace in replacements:
            cleaned_text = re.sub(rplace.pattern, rplace.replacement, cleaned_text, flags=re.DOTALL) if not rplace.description == 'Header' else re.sub(rplace.pattern, rplace.replacement, cleaned_text)
        return cleaned_text
    
    def fetch_level(self, identifier, level):
        with db.engine.connect() as connection:
            query = text("SELECT * FROM severity_level_data;")
            query_result = connection.execute(query).fetchall()
            level_df = pd.DataFrame(query_result)
            filt_df = level_df[(level_df['troubleshoot_level'] == level) & (level_df['identifier'].str.contains(identifier))]
            if filt_df.empty:
                filt_df = level_df[(level_df['troubleshoot_level'].str.contains(level)) & (level_df['identifier'].str.contains(identifier))]
            
            if not filt_df.empty:
                level_content = filt_df.iloc[0]['level_content'] if filt_df.iloc[0]['level_content'] else ''
                troubleshoot_flow = filt_df.iloc[0]['troubleshoot_flow'] if filt_df.iloc[0]['troubleshoot_flow'] else ''
            else:
                level_content = ''
                troubleshoot_flow = ''
            return level_content, troubleshoot_flow
    
    def fetch_contact_data(self, identifier):
        with db.engine.connect() as connection:
            query = text("SELECT * FROM contact_information;")
            query_result = connection.execute(query).fetchall()
            contact_df = pd.DataFrame(query_result)
            filt_df = contact_df[contact_df['identifier'].str.contains(identifier)]
            if not filt_df.empty:
                contact_content = filt_df.iloc[0]['contact_page_content'] if filt_df.iloc[0]['contact_page_content'] else ''
            else:
                contact_content = ''
            return contact_content