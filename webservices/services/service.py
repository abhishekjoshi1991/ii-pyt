import re
import os
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from langchain_core.retrievers import BaseRetriever
from typing import List
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from flask import jsonify, make_response
from dotenv import load_dotenv
from webservices.models.models import VectorDBResponse, db, MasterCorrectSOP, MasterProjectType, MasterModuleStateAgent, SOPFeedback
from webservices.services import qa_chain, client
from config import SQLALCHEMY_DATABASE_URI_2, email_delimiter_1, email_delimiter_2
from webservices.models.models import create_engine_from_uri

load_dotenv()

classname = os.getenv('WEAVIATE_CLASS')

class VectorDB:
    # Log vectordb output to sql database
    def log_data(self, module, state, agent, query, data, user):
        time_stamp = datetime.now()
        current_time = time_stamp.strftime("%Y-%m-%d %H:%M:%S")
        json_data_list = []
        japanese_main_keys = ['識別子', 'モジュール', 'エージェント', '状態', 'ウィキタイトル', 'ウィキコンテンツ', 'ページ']
        japanese_vector_data = []
        for record in data:
            lines = record.page_content
            identifier_match = re.search(r'識別子「([^」]+)」', lines)
            module_match = re.search(r'モジュールは「([^」]+)」', lines)
            agent_match = re.search(r'エージェントは「([^」]+)」', lines)
            state_match = re.search(r'状態は「([^」]*)」', lines)
            wiki_title_match = re.search(r'ウィキタイトルは「([^」]+)」', lines)
            wiki_content_match = re.search(r'ウィキコンテンツは「([^」]+)」', lines)
            page_number_match = re.search(r'ページは「([^」]+)」', lines)
            
            identifier = identifier_match.group(1) if identifier_match else ''
            module_value = module_match.group(1) if module_match else ''
            agent_value = agent_match.group(1) if agent_match else ''
            state_value = state_match.group(1) if state_match else ''
            wiki_title = wiki_title_match.group(1) if wiki_title_match else ''
            wiki_content = wiki_content_match.group(1) if wiki_content_match else ''
            page = page_number_match.group(1) if page_number_match else ''
            data_list = [identifier, module_value, agent_value, state_value, wiki_title, wiki_content, page]
            japanese_vector_data.append(data_list)

        df = pd.DataFrame(japanese_vector_data, columns=japanese_main_keys)
        df['json_data'] = df.apply(lambda row: row.to_dict(), axis=1)
        df['module'] = module
        df['state'] = state
        df['agent'] = agent
        df['query'] = query
        df['user'] = user
        json_data_list = df['json_data'].to_list()
        objects = []
        for index, row in df.iterrows():
            objects.append(VectorDBResponse(module=row['module'],
                                        state=row['state'],
                                        agent=row['agent'],
                                        query=row["query"],
                                       user=row["user"],
                                       solution=row["json_data"],
                                       created_at = current_time,
                                       ))
        db.session.bulk_save_objects(objects)
        db.session.commit()
        return json_data_list
    
    def query_formation(self, parsed_project, module, state, agent):
        project_match = MasterProjectType.query.filter(MasterProjectType.identifier.like(f'%{parsed_project}%')).first()
        if project_match:
            module_check = project_match.module
            state_check = project_match.state
            agent_check = project_match.agent
            if module_check and state_check and agent_check:
                prepared_query = f"識別子「{parsed_project}」の場合、モジュールは「{module}」とエージェントは「{agent} またはすべて」と障害状態は「{state}」であればページ取得してください。"
            elif module_check and agent_check:
                prepared_query = f"識別子「{parsed_project}」の場合、モジュールは「{module}」とエージェントは「{agent} またはすべて」であればページ取得してください。"
            elif module_check and state_check:
                prepared_query = f"識別子「{parsed_project}」の場合、モジュールは「{module}」と障害状態は「{state}」であればページ取得してください。"
            elif agent_check and state_check:
                prepared_query = f"識別子「{parsed_project}」の場合、エージェントは「{agent} またはすべて」と障害状態は「{state}」であればページ取得してください。"
            elif module_check:
                prepared_query = f"識別子「{parsed_project}」の場合、モジュールは「{module}」であればページ取得してください。"
            elif state_check:
                prepared_query = f"識別子「{parsed_project}」の場合、と障害状態は「{state}」であればページ取得してください。"
            elif agent_check:
                prepared_query = f"識別子「{parsed_project}」の場合、エージェントは「{agent} またはすべて」であればページ取得してください。"
            else:
                return ''
            return prepared_query
        else:
            return ''
    
    def source_doc_info_extract(self, source_documents):
        source_docs_info = {}
        pattern_module = r'モジュールは「(.*?)」'
        pattern_state = r'状態は「(.*?)」'
        pattern_agent = r'エージェントは「(.*?)」'
        pattern_identifier = r'識別子「(.*?)」'
        pattern_wiki_title = r'ウィキタイトルは「(.*?)」'
        pattern_page_id = r'ページは「(\d+)」'
        
        for source in source_documents:
            match_module = re.search(pattern_module, source.page_content)
            match_state = re.search(pattern_state, source.page_content)
            match_agent = re.search(pattern_agent, source.page_content)
            match_identifier = re.search(pattern_identifier, source.page_content)
            match_wiki = re.search(pattern_wiki_title, source.page_content)
            match_page = re.search(pattern_page_id, source.page_content)

            source_docs_identifier = match_identifier.group(1) if match_identifier else ''
            source_docs_module = match_module.group(1) if match_module else ''
            source_docs_agent = match_agent.group(1) if match_agent else ''
            source_docs_state = match_state.group(1) if match_state else ''
            source_docs_wiki_title = match_wiki.group(1) if match_wiki else ''
            source_docs_page_id = match_page.group(1)
            data_values = {
                '識別子': source_docs_identifier, 
                'モジュール': source_docs_module, 
                'エージェント': source_docs_agent, 
                '状態': source_docs_state,
                'wiki': source_docs_wiki_title
            }
            
            source_docs_info.update({int(source_docs_page_id): data_values})
        return source_docs_info

    def get_SOP(self, email_to, module, state, agent, user):
        if email_delimiter_1 and email_delimiter_2:
            email_split = email_to.split(email_delimiter_1)[0].split(email_delimiter_2)
            parsed_project = '-'.join(email_split[:2]) if len(email_split) > 2 else email_split[0]
        else:
            parsed_project = email_to.split(email_delimiter_1)[0]
        prepared_query = self.query_formation(parsed_project, module, state, agent)
        page_numbers = []
        if prepared_query:
            llm_response = self.get_llm_output(prepared_query)
            if llm_response:
                explainable_data = []
                result_vals = {}
                try:
                    if os.getenv('MODEL') == 'TheBloke/Llama-2-7B-Chat-GGML':
                        page_numbers = [int(match) for match in re.findall(r'\d+', llm_response['result'])]
                    else:
                        match = re.search(r'Helpful answer.*?(\d+(?:,\s*\d+)*)', llm_response['result'], re.DOTALL)
                        page_numbers = list(map(int, match.group(1).split(',')))
                    final_output = []
                    sop_links = []
                    source_documents = llm_response['source_documents']
                    source_docs_info = self.source_doc_info_extract(source_documents)
                    for i in page_numbers:
                        if int(i) in source_docs_info:
                            sop_links.append({'SOP_url': self.generate_sop_link(i), **source_docs_info[int(i)]})
                            final_output.append({'page': i})
                    combined_list = [{**dict1, **dict2} for dict1, dict2 in zip(final_output, sop_links)]
                    result_vals.update({'result': combined_list})

                    vector_db_source_docs = self.log_data(module, state, agent, prepared_query, source_documents, user)
                    input_parameters = {'モジュール': module, '状態': state, 'エージェント': agent, 'query': prepared_query, 'source_documents': vector_db_source_docs}
                    explainable_data.append(input_parameters)
                    result_vals.update({'explainable_data': explainable_data})
                    return result_vals
                except Exception as e:
                    return "結果を取得できません"
        else:
            return "指定されたプロジェクトのエントリが master_project_type テーブルに存在しません"
              
    def get_llm_output(self, query):
        retriever = CustomRetriever(question=query)
        qa_chain.retriever = retriever
        response = qa_chain.invoke({'query': query})
        return response

    def generate_sop_link(self, page_id):
        engine = create_engine_from_uri(SQLALCHEMY_DATABASE_URI_2)
        with engine.connect() as connection:
            sql_query_wiki_pages = text(f'select wiki_id, title from wiki_pages where id in ({page_id});')
            query_result = connection.execute(sql_query_wiki_pages)
            wiki_pages_records = query_result.fetchall()
            wiki_id = wiki_pages_records[0][0]
            wiki_title = wiki_pages_records[0][1]

            sql_query_projects = text(f'select identifier from projects where id in ({wiki_id});')
            project_query_result = connection.execute(sql_query_projects)
            project_records = project_query_result.fetchall()
            project_identifier = project_records[0][0]

            redmine_url = f'{os.getenv("REDMINE_HTTP_PROTOCOL")}://{os.getenv("REDMINE_HOST")}/projects/{project_identifier}/wiki/{wiki_title}'
        return redmine_url
    
    def extract_email_data(self, email_text, user):
        try:
            email_match = re.search(r'To:(.*?)(\w+:)', email_text, re.DOTALL)
            if email_match:
                email = email_match.group(1).strip()
            else:
                email_match_2 = re.search(r'To: (.*?)From', email_text)
                email = email_match_2.group(1).strip() if email_match_2 else None

            email_id = email.split(',')[0]
            
            agent_match = re.search(r"エージェント\s*:\s*(.*?)\n", email_text)
            if agent_match:
                agent = agent_match.group(1).strip()
            else:
                agent_match_2 = re.search(r'エージェント\s+: (.*?)\sモジュール', email_text)
                agent = agent_match_2.group(1).strip() if agent_match_2 else None

            module_match = re.search(r"モジュール\s*:\s*(.*?)\n", email_text)
            if module_match:
                module = module_match.group(1).strip()
            else:
                module_match_2 = re.search(r'モジュール\s+: (.*?)\s障害内容', email_text)
                module = module_match_2.group(1).strip() if module_match_2 else None

            state_match = re.search(r"障害内容\s*:\s*(.*?)\n", email_text)
            if state_match:
                state = state_match.group(1).strip() if state_match else None
            else:
                state_match_2 = re.search(r'障害内容\s+: (.*?)\s監視対象の現在の値', email_text)
                state = state_match_2.group(1).strip() if state_match_2 else None

            vals = {'to_email': email_id, 
                    'agent': agent, 
                    'module': module, 
                    'state': state}
            res = self.get_SOP(email_id, module, state, agent, user)
            return res
        except Exception as e:
            return '提供された電子メールのテキストから情報を抽出できません'
    
    def get_module_state_agent(self, email_text):
        try:
            email_match = re.search(r'To:(.*?)(\w+:)', email_text, re.DOTALL)
            if email_match:
                email = email_match.group(1).strip()
            else:
                email_match_2 = re.search(r'To: (.*?)From', email_text)
                if email_match_2:
                    email = email_match_2.group(1).strip()
                else:
                    email_match_3 = re.search(r'To\s*:\s*(.*?)\n', email_text)
                    email = email_match_3.group(1).strip() if email_match_3 else None
            email_id = email.split(',')[0]
            
            agent_match = re.search(r"エージェント\s*:\s*(.*?)\n", email_text)
            if agent_match:
                agent = agent_match.group(1).strip()
            else:
                agent_match_2 = re.search(r'エージェント\s+: (.*?)\sモジュール', email_text)
                agent = agent_match_2.group(1).strip() if agent_match_2 else None

            module_match = re.search(r"モジュール\s*:\s*(.*?)\n", email_text)
            if module_match:
                module = module_match.group(1).strip()
            else:
                module_match_2 = re.search(r'モジュール\s+: (.*?)\s障害内容', email_text)
                module = module_match_2.group(1).strip() if module_match_2 else None

            state_match = re.search(r"障害内容\s*:\s*(.*?)\n", email_text)
            if state_match:
                state = state_match.group(1).strip() if state_match else None
            else:
                state_match_2 = re.search(r'障害内容\s+: (.*?)\s監視対象の現在の値', email_text)
                state = state_match_2.group(1).strip() if state_match_2 else None
            
            # parsed_project = email_id.split('@')[0].split('-')[0]
            parsed_project = email_id.split('@')[0]
            parsed_project = '-'.join(parsed_project.split('-')[:-1])

            vals = {'project': parsed_project, 
                    'agent': agent, 
                    'module': module, 
                    'state': state
                    }
            return vals
        except Exception as e:
            return '提供された電子メールのテキストから情報を抽出できません'
    
    def log_correct_SOP(self, page_number, prepared_query, generated_sop, correct_sop, module, state, agent, project, sop_type, user_email):
        with db.engine.connect() as connection:
            sql_query = text(f"SELECT * FROM master_module_state_agent WHERE module='{module}' and state='{state}' and agent='{agent}' and project='{project}' and user_email='{user_email}'")
            query_result = connection.execute(sql_query)
            match_records = query_result.first()
            
            if not match_records:
                new_record = MasterModuleStateAgent(module=module, state=state, agent=agent, project=project, user_email=user_email)
                db.session.add(new_record)
                db.session.commit()
                record_id = new_record.id
            else:
                record_id = match_records[0]

            query_correct_sop = text(f"SELECT * FROM correct_sop WHERE page_number='{page_number}' and mod_state_agent_id='{record_id}'")
            query_result_correct_sop = connection.execute(query_correct_sop)
            record_exists = query_result_correct_sop.first()
            if not record_exists:
                record_to_insert = MasterCorrectSOP(mod_state_agent_id=record_id, page_number=page_number, prepared_query=prepared_query, generated_sop=generated_sop, correct_sop=correct_sop, sop_type=sop_type)
                db.session.add(record_to_insert)
                db.session.commit()
                return 'データは正常に保存されました'
            else:
                return 'すでに完了しました'
            
    def log_generated_sop_feedback(self, module, state, agent, project, user_email, generated_sop, customer_specific_sop, modified_generated_sop, modified_customer_specific_sop, feedback):
        with db.engine.connect() as connection:
            sql_query = text(f"SELECT * FROM master_module_state_agent WHERE module='{module}' and state='{state}' and agent='{agent}' and project='{project}' and user_email='{user_email}'")
            query_result = connection.execute(sql_query)
            match_records = query_result.first()
            
            if not match_records:
                new_record = MasterModuleStateAgent(module=module, state=state, agent=agent, project=project, user_email=user_email)
                db.session.add(new_record)
                db.session.commit()
                record_id = new_record.id
            else:
                record_id = match_records[0]

            query = text(f"SELECT * FROM sop_feedback WHERE msa_id='{record_id}'")
            query_result = connection.execute(query)
            record_exists = query_result.first()
            if not record_exists:
                record_to_insert = SOPFeedback(msa_id=record_id, generated_sop=generated_sop, customer_specific_sop=customer_specific_sop, modified_generated_sop=modified_generated_sop, modified_customer_specific_sop=modified_customer_specific_sop, feedback=feedback)
                db.session.add(record_to_insert)
            else:
                record = db.session.query(SOPFeedback).filter_by(id=record_exists[0]).one()
                record.generated_sop = generated_sop
                if customer_specific_sop != '':
                    record.customer_specific_sop = customer_specific_sop
                else:
                    record.customer_specific_sop = customer_specific_sop
                    record.modified_generated_sop = modified_generated_sop
                record.modified_customer_specific_sop = modified_customer_specific_sop
                record.feedback = feedback
            db.session.commit()
            return make_response(
                        jsonify({
                            "message": "データは正常に保存されました"
                        }), 
                        200
                    )

    def remove_sop_from_vectordb(self, page_id):
        classname= os.getenv("WEAVIATE_CLASS")
        response = (
            client.query
            .get(classname, ["final_document"])
            .with_where({
                        "path": ["final_document"],
                        "operator": "Equal",
                        "valueText": f"{page_id}",
                })
            .with_limit(3)
            .with_additional(['id']) 
            .do()
        )
        identical_matches = response['data']['Get'][classname]
        if identical_matches:
            for record in identical_matches:
                page_number_match = re.search(r'ページは「([^」]+)」', record['final_document'])
                if page_number_match:
                    page_id_from_match = int(page_number_match.group(1))
                    if page_id_from_match == page_id:
                        doc_id = record['_additional']['id']
                        client.data_object.delete(
                            uuid=doc_id,
                            class_name=classname
                        )
                        return make_response(
                                jsonify({
                                    "message": f"対象となるコンテンツがベクター データベースから正常に削除されました"
                                }), 
                                200
                            )
            else:
                return make_response(
                    jsonify({
                        "message": "指定されたSOPのデータ存在しませんので再確認下さい"
                    }), 
                    404
                )
        else:
            return make_response(
                    jsonify({
                        "message": "指定されたSOPのデータ存在しませんので再確認下さい"
                    }), 
                    404
                )
        
    def project_specific_level(self, identifier):
        with db.engine.connect() as connection:
            sql_query = text(f"SELECT * FROM severity_level_data WHERE identifier LIKE '%{identifier}%'")
            query_result = connection.execute(sql_query)
            match_records = data_dicts = query_result.mappings().all()
            troubleshoot_levels = []
            if match_records:
                troubleshoot_level_list = [row['troubleshoot_level'] for row in data_dicts if 'troubleshoot_level' in row]
                troubleshoot_levels = sorted(list(set(troubleshoot_level_list)))
                return make_response(
                        jsonify({
                            "troubleshoot_level": troubleshoot_levels
                        }), 
                        200
                    )
            else:
                return make_response(
                        jsonify({
                            "troubleshoot_level": troubleshoot_levels
                        }), 
                        404
                    )


class CustomRetriever(BaseRetriever):
    question : str

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        module_match = re.search(r'モジュールは「([^」]+)」', self.question)
        identifier_match = re.search(r'識別子「([^」]+)」', self.question)
        module = ''
        identifier = ''
        if module_match:
            module = module_match.group(1)
        if identifier_match:
            identifier = identifier_match.group(1)
        response = (
                client.query
                .get(classname, ["final_document"])
                .with_bm25(f"{identifier}, {module}")
                .with_additional(['score'])
                .with_limit(4)
                .do()
        )
        search_documents = response['data']['Get'][classname]
        if not search_documents:
            response = (
                client.query
                .get(classname, ["final_document"])
                .with_where({
                    "path": ["final_document"],
                    "operator": "ContainsAny",
                    "valueText": [identifier, module]
                })
                .with_limit(4)
                .do()
            )
            search_documents = response['data']['Get'][classname]

        document =  []
        for item in search_documents:
            page = Document(page_content=item['final_document'])
            document.append(page)
        return document
