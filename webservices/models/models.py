from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON
from sqlalchemy import create_engine

db = SQLAlchemy()

def create_engine_from_uri(uri):
    engine = create_engine(uri)
    return engine

class VectorDBResponse(db.Model):
    __tablename__ = 'vector_db_response'
    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.VARCHAR(200), nullable=True)
    state = db.Column(db.VARCHAR(200), nullable=True)
    agent = db.Column(db.VARCHAR(200), nullable=True)
    query = db.Column(db.VARCHAR(200), nullable=True)
    solution = db.Column(JSON)
    user = db.Column(db.VARCHAR(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=True)


class MasterProjectType(db.Model):
    __tablename__ = 'master_project_type'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.VARCHAR(200), nullable=True)
    type = db.Column(db.VARCHAR(200), nullable=True)
    module = db.Column(db.VARCHAR(200), nullable=True)
    state = db.Column(db.VARCHAR(200), nullable=True)
    agent = db.Column(db.VARCHAR(200), nullable=True)
    sop_column = db.Column(db.VARCHAR(200), nullable=True)
    sop_delimeter = db.Column(db.VARCHAR(200), nullable=True)
    special_case1 = db.Column(db.VARCHAR(200), nullable=True)
    

class MasterModuleStateAgent(db.Model):
    __tablename__ = 'master_module_state_agent'
    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.VARCHAR(200), nullable=True)
    state = db.Column(db.VARCHAR(200), nullable=True)
    agent = db.Column(db.VARCHAR(200), nullable=True)
    project = db.Column(db.VARCHAR(200), nullable=True)
    user_email = db.Column(db.VARCHAR(200), nullable=True)

    
class MasterCorrectSOP(db.Model):
    __tablename__ = 'correct_sop'
    id = db.Column(db.Integer, primary_key=True)
    mod_state_agent_id = db.Column(db.Integer, db.ForeignKey('master_module_state_agent.id'), nullable=False)
    page_number = db.Column(db.Integer, nullable=True)
    prepared_query = db.Column(db.VARCHAR(200), nullable=True)
    generated_sop = db.Column(db.VARCHAR(200), nullable=True)
    correct_sop = db.Column(db.VARCHAR(200), nullable=True)
    sop_type = db.Column(db.VARCHAR(200), nullable=True)


class SeverityLevel(db.Model):
    __tablename__ = 'severity_level_data'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.VARCHAR(200), nullable=True)
    troubleshoot_level = db.Column(db.VARCHAR(200), nullable=True)
    troubleshoot_flow = db.Column(db.VARCHAR(200), nullable=True)
    troubleshoot_descripton = db.Column(db.VARCHAR(200), nullable=True)
    level_content = db.Column(db.VARCHAR(1000), nullable=True)


class ContactInformation(db.Model):
    __tablename__ = 'contact_information'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.VARCHAR(200), nullable=True)
    contact_page_content = db.Column(db.VARCHAR(2000), nullable=True)


class PostprocessPattern(db.Model):
    __tablename__ = 'postprocess_pattern'
    id = db.Column(db.Integer, primary_key=True)
    pattern = db.Column(db.VARCHAR(200), nullable=False)
    replacement = db.Column(db.VARCHAR(200), nullable=False)
    description = db.Column(db.VARCHAR(200), nullable=True)


class SOPFeedback(db.Model):
    __tablename__ = 'sop_feedback'
    id = db.Column(db.Integer, primary_key=True)
    msa_id = db.Column(db.Integer, db.ForeignKey('master_module_state_agent.id'), nullable=False)
    generated_sop = db.Column(db.Text, nullable=True)
    customer_specific_sop = db.Column(db.Text, nullable=True)
    modified_generated_sop = db.Column(db.Text, nullable=True)
    modified_customer_specific_sop = db.Column(db.Text, nullable=True)
    feedback = db.Column(db.VARCHAR(500), nullable=True)