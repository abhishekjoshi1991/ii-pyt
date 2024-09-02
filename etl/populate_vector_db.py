import os
import re
import textile
import weaviate
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
from extract_module_info import GetParentChildData
from dotenv import load_dotenv
load_dotenv()

weaviate_class = os.getenv("WEAVIATE_CLASS")
obj = GetParentChildData()

def create_document(row):
    return f"識別子「{row['identifier']}」のために、モジュールは「{row['module']}」、エージェントは「{row['agent']}」、状態は「{row['state']}」、ウィキタイトルは「{row['title']}」およびウィキコンテンツは「{row['processed_text']}」であれば、ページは「{row['id']}」です。"

def convert_table_to_text(overview_section):
    html_content = textile.textile(overview_section)
    table_pattern = re.compile(r'<table>.*?</table>', re.DOTALL)
    tables = re.findall(table_pattern, html_content)
    if tables:
        if len(tables) == 1:
            table = tables[0].replace('\n', '、')
            soup = BeautifulSoup(table, 'html.parser')
            df = pd.read_html(StringIO(str(soup)))[0]
            numeric_columns = pd.to_numeric(df.columns, errors='coerce').notna()
            if any(numeric_columns):
                df['japanese_text'] = df[0] + 'は' + df[1] + '。'
                japanese_sentence = '\n'.join(df['japanese_text'])
            else:
                for index, row in df.iterrows():
                    sentence_parts = []
                    for col_name, value in row.items():
                        sentence_parts.append(f"{col_name} は {value}")
                    japanese_sentence = '。'.join(sentence_parts)
            
            index_table_start = html_content.find('<table>')
            index_table_end = html_content.find('</table>') + len('</table>')
            final_sentence = html_content.replace(html_content[index_table_start:index_table_end], japanese_sentence)
            soup_obj = BeautifulSoup(final_sentence, 'html.parser')
            plain_text = soup_obj.get_text(separator=' ',strip=True)
            return plain_text
    else:
        return overview_section

def get_overview(text):
    pattern_get_overview = re.compile(r'h\d\.\s*概要(.*?)h\d\.', re.DOTALL)
    pattern_overview_match = pattern_get_overview.search(text)
    
    pattern_html_heads = re.compile(r'h\d\.(.*?)(?=(?:h[1-6]\.|$))', re.DOTALL)
    pattern_html_heads_match = pattern_html_heads.findall(text)
    
    if pattern_overview_match:
        overview_section = pattern_overview_match.group(1).strip()
        return overview_section
    elif pattern_html_heads_match:
        if len(pattern_html_heads_match) >= 2:
            if pattern_html_heads_match[1].strip() != "対応手順":
                result_text = "\n".join(pattern_html_heads_match[:2])
            else:
                result_text = pattern_html_heads_match[0] 
        else:
            result_text = pattern_html_heads_match.group(1).strip()
        return result_text
    else:
        return text
        
def get_formatted_table(text):
    pattern_get_overview = re.compile(r'h\d\.\s*概要(.*?)h\d\.', re.DOTALL)
    pattern_overview_match = pattern_get_overview.search(text)
    
    pattern_html_heads = re.compile(r'h\d\.(.*?)(?=(?:h[1-6]\.|$))', re.DOTALL)
    pattern_html_heads_match = pattern_html_heads.findall(text)
    
    if pattern_overview_match:
        overview_section = pattern_overview_match.group(1).strip()
        formatted_table_text = convert_table_to_text(overview_section)
        return formatted_table_text
    elif pattern_html_heads_match:
        if len(pattern_html_heads_match) >= 2:
            if pattern_html_heads_match[1].strip() != "対応手順":
                result_text = "\n".join(pattern_html_heads_match[:2])
            else:
                result_text = pattern_html_heads_match[0] 
        else:
            result_text = pattern_html_heads_match.group(1).strip()
        formatted_table_text = convert_table_to_text(result_text)
        return formatted_table_text
    else:
        return text

df = obj.get_module_state_agent()
df = df.fillna('')
df['identifier_new'] = df['identifier'].apply(lambda x: '-'.join(x.split('-')[:2]) if len(x.split('-')) > 2 else x.split('-')[0])

df['text'] = df['text'].apply(lambda x: x.replace('\n', ' '))
df['text'] = df['text'].apply(lambda x: x.replace('\n\n', ' '))
df['text'] = df['text'].apply(lambda x: x.replace('_x000D_', ''))

df['overview_text'] = df['text'].apply(get_overview)
df['processed_text'] = df['text'].apply(get_formatted_table)
df['final_document'] = df.apply(create_document, axis=1)

client = weaviate.Client("http://localhost:8080")

class_exists = client.schema.exists(class_name=weaviate_class)
if class_exists:
    client.schema.delete_class(weaviate_class)

# Create weaviate schema
class_obj = {'class': weaviate_class,
    "properties": [
{
    "dataType": ["text"],
    "name": "final_document",
}
    ]
}

if not class_exists:
    client.schema.create_class(class_obj)

# Create data objects
client.batch.configure(batch_size=100)  # Configure batch
with client.batch as batch:  # Initialize a batch process
    for i, d in df.iterrows():  # Batch import data
        properties = {
            "final_document": d['final_document']
        }
        batch.add_data_object(
            data_object=properties,
            class_name=weaviate_class
        )
