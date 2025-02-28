from evaluators.langchain_evaluator_base import LangChainBaseEvaluator
from copyleaks.copyleaks import Copyleaks
from copyleaks.exceptions.command_error import CommandError
from copyleaks.models.submit.ai_detection_document import NaturalLanguageDocument, SourceCodeDocument
from copyleaks.models.export import *
import os
import uuid

class ScanResultError(Exception):
    """Exception raised for errors in the scan results."""
    def __init__(self, message):
        super().__init__(message)

class AIScanner:
    def __init__(self, email=os.getenv("COPYLEAKS_EMAIL_ADDRESS", None), 
                 key=os.getenv("COPYLEAKS_KEY", None), 
                 hook_server=os.getenv("WEBHOOK_SERVER_URL")) -> None:
        self.EMAIL_ADDRESS = email
        self.KEY = key
        self.hook_server_url = hook_server

        # Initialize Copyleaks login and database connection
        self.login_to_copyleaks()
       
    def login_to_copyleaks(self):
        try:
            self.auth_token = Copyleaks.login(self.EMAIL_ADDRESS, self.KEY)
        except CommandError as ce:
            response = ce.get_response()
            print(f"An error occurred (HTTP status code {response.status_code}):")
            print(response.content)
            raise ConnectionError("Failed to login to Copyleaks")

    def scan_text(self, content, scan_id="testest234"):
        natural_language_submission = NaturalLanguageDocument(content)
        natural_language_submission.set_sandbox(False)
        response = Copyleaks.AiDetectionClient.submit_natural_language(self.auth_token, scan_id, natural_language_submission)
        if "results" in response:
            return response["results"]
        else:
            raise ScanResultError(str(response.get("error", {"error":"Something went wrong"})))
    
    def scan_code(self, content, scan_id="testest234"):
        source_code_submission = SourceCodeDocument(content, "code")
        source_code_submission.set_sandbox(False)
        response = Copyleaks.AiDetectionClient.submit_natural_language(self.auth_token, scan_id, source_code_submission)
        if "results" in response:
            return response["results"]
        else:
            raise ScanResultError(str(response.get("error", {"error":"Something went wrong"})))
        
        
        
    def scan_combine(self, content, scan_id="combinedScan123"):
        try:
            content_length = len(content)
            while content_length < 255:
                content += content  # Append content to itself until it reaches the minimum length
                content_length = len(content)
            if content_length > 25000:
                content = content[:25000]  # Truncate content if it exceeds the maximum length
            text_results = self.scan_text(content, scan_id)
            code_results = self.scan_code(content, scan_id)
            
            combined_results = text_results + code_results
            for result in combined_results:
                if result.get('classification', 1) == 2:
                    return "FAIL"
            return "PASS"
        except Exception as e:
            raise ScanResultError(f"No credit to perform operations or something went wrong: {e}")
        



class EvaluationAIChecker(LangChainBaseEvaluator):
    def create_prompt(self, input_data):
        return input_data

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=None,
        format_to_issues_scores=False,
    ):
        scannner = AIScanner()

        # happen here
        user_prompt_content = input_data.get("user_prompt", {}).get("content")
        ideal_response_content = input_data.get("alternative_last_ai_reply", {}).get("content")
        
        to_sacn= user_prompt_content if user_prompt_content else ideal_response_content
        scan_id = str(uuid.uuid4())
        score = scannner.scan_combine(content=to_sacn, scan_id=scan_id)
        
        result = {
            "evaluation_result": score,
            "explanation_for_the_evaluation_result": "Content was generated with AI",
        }
       

        return {"result":result}

