from webservices.dto.dtos import api
from flask_restx import Resource, fields, reqparse, abort
from webservices.services.service import VectorDB
from webservices.services.generate_sop import GenerateSOP
import urllib.parse

api = api
vectordb = VectorDB()
generate_sop = GenerateSOP()

resource_fields = api.model('Request', {
    'email_to': fields.String(required=True),
    'module': fields.String(required=True),
    'state': fields.String(required=True),
    'agent': fields.String(required=True),
    'user': fields.String(required=True)
})

resource_fields_for_correct_sop = api.model('Request1', {
    'page_number': fields.Integer(required=True),
    'prepared_query': fields.String(required=True),
    'generated_sop': fields.String(required=True),
    'correct_sop': fields.String(required=True),
    'module': fields.String(required=True),
    'state': fields.String(required=True),
    'agent': fields.String(required=True),
    'project': fields.String(required=True),
    'sop_type': fields.String(required=True),
    'user_email': fields.String(required=True)
})

resource_fields_for_remove_sop = api.model('Request2', {
    'page_number': fields.Integer(required=True),
})

resource_fields_model_op_free_text = api.model('Request3', {
    'query': fields.String(required=True),
    'customer_specific': fields.Boolean(required=True, default=False),
    'level': fields.String(required=True, default='')
})

resource_fields_for_sop_by_paramters = api.model('Request4', {
    'identifier': fields.String(required=True),
    'module': fields.String(required=True),
    'state': fields.String(required=True),
    'agent': fields.String(required=True),
    'customer_specific': fields.Boolean(required=True, default=False),
    'level': fields.String(required=False, default='')
})

resource_fields_for_generated_sop_feedback = api.model('Request5', {
    'module': fields.String(required=True),
    'state': fields.String(required=True),
    'agent': fields.String(required=True),
    'project': fields.String(required=True),
    'user_email': fields.String(required=True),
    'generated_sop': fields.String(required=True, default=''),
    'customer_specific_sop': fields.String(required=True, default=''),
    'modified_generated_sop': fields.String(required=True, default=''),
    'modified_customer_specific_sop': fields.String(required=True, default=''),
    'feedback': fields.String(required=True, default='')
})

resource_fields_for_project_specific_level = api.model('Request6', {
    'identifier': fields.String(required=True),
})

parser = reqparse.RequestParser()
parser.add_argument('email_text', type=str, help='Description for email text')
parser.add_argument('user', type=str, help='User Name')

@api.route('/get_SOP')
class GetQueryResult(Resource):
    @api.expect(resource_fields, validate = True)
    def post(self):
        """This API retrieves search results for the user's query."""
        email_to = api.payload['email_to']
        module = api.payload['module']
        state = api.payload['state']
        agent = api.payload['agent']
        user = api.payload['user']
        return vectordb.get_SOP(email_to, module, state, agent, user)


@api.route('/get_correct_SOP')
class CorrectSOP(Resource):
    @api.expect(resource_fields_for_correct_sop)
    def post(self):
        """This API logs the correct SOP data to the database."""
        page_number = api.payload['page_number']
        prepared_query = api.payload['prepared_query']
        generated_sop = api.payload['generated_sop']
        correct_sop = api.payload['correct_sop']
        module = api.payload['module']
        state = api.payload['state']
        agent = api.payload['agent']
        project = api.payload['project']
        sop_type = api.payload['sop_type']
        user_email = api.payload['user_email']
        return vectordb.log_correct_SOP(page_number, prepared_query, generated_sop, correct_sop, module, state, agent, project, sop_type, user_email)


@api.route('/extract_email_data')
class ExtractEmailData(Resource):
    @api.expect(parser, validate=True)
    def post(self):
        """This API extracts information from a provided alert email."""
        args = parser.parse_args()
        email_text = args['email_text']
        user = args['user']
        email_text = urllib.parse.unquote(email_text)
        user = urllib.parse.unquote(user)
        return vectordb.extract_email_data(email_text, user)

parser_for_module = reqparse.RequestParser()
parser_for_module.add_argument('email_text', type=str, help='Alert Email Text')

@api.route('/get_ModuleStateAgent')
class GetModuleStateAgent(Resource):
    @api.expect(parser_for_module, validate=True)
    def post(self):
        """This API extracts information such as module, state, and agent from a provided alert email."""
        args = parser_for_module.parse_args()
        email_text = args['email_text']
        email_text = urllib.parse.unquote(email_text)
        return vectordb.get_module_state_agent(email_text)


@api.route('/remove_sop')
class RemoveSOP(Resource):
    @api.expect(resource_fields_for_remove_sop, validate=True)
    def post(self):
        """This is an API for removing a record from a vector database associated with a specific page ID"""
        page_id = api.payload['page_number']
        return vectordb.remove_sop_from_vectordb(page_id)

    
@api.route('/generate_sop_free_text')
class GenerateSOPFreeText(Resource):
    @api.expect(resource_fields_model_op_free_text, validate = True)
    def post(self):
        """This API is designed to generate a Standard Operating Procedure (SOP) based on the user's query."""
        query = api.payload['query']
        customer_specific = api.payload['customer_specific']
        level = api.payload['level']
        if not query:
            abort(400, message="Parameter 'query' is empty. Please provide a valid query.")
        return generate_sop.get_query_output(query, customer_specific, level)


@api.route('/generate_sop_by_parameters')
class GetSOPByParameters(Resource):
    @api.expect(resource_fields_for_sop_by_paramters, validate = True)
    def post(self):
        """This API is designed to generate a Standard Operating Procedure (SOP) based on the parameters: identifier, module, state, and agent."""
        identifier = api.payload['identifier']
        module = api.payload['module']
        state = api.payload['state']
        agent = api.payload['agent']
        customer_specific = api.payload['customer_specific']
        level = api.payload['level']
        query = f"識別子が「{identifier}」、モジュールが「{module}」、エージェントが「{agent}」、障害状態が「{state}」の場合、対応手順はどうなるでしょうか？"
        return generate_sop.get_sop_by_parameters(query, customer_specific, level)
    

@api.route('/log_sop_feedback')
class LogSOPFeedback(Resource):
    @api.expect(resource_fields_for_generated_sop_feedback, validate = True)
    def post(self):
        """This API records the feedback comments related to the generated SOP in the database."""
        module = api.payload['module']
        state = api.payload['state']
        agent = api.payload['agent']
        project = api.payload['project']
        user_email = api.payload['user_email']
        generated_sop = api.payload['generated_sop']
        customer_specific_sop = api.payload['customer_specific_sop']
        modified_generated_sop = api.payload['modified_generated_sop']
        modified_customer_specific_sop = api.payload['modified_customer_specific_sop']
        feedback = api.payload['feedback']
        return vectordb.log_generated_sop_feedback(module, state, agent, project, user_email, generated_sop, customer_specific_sop, modified_generated_sop, modified_customer_specific_sop, feedback)
    

@api.route('/project_specific_level')
class ProjectSpecificLevel(Resource):
    @api.expect(resource_fields_for_project_specific_level, validate = True)
    def post(self):
        """This API takes the project name as a parameter and returns a list of associated levels for that project."""
        identifier = api.payload['identifier']
        return vectordb.project_specific_level(identifier)
