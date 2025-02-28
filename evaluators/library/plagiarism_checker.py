
from gevent.pool import Pool
from langchain.prompts.base import BasePromptTemplate
from app.logging_config import logger
import requests
import time
import json
import os
from evaluators.langchain_evaluator_base import LangChainBaseEvaluator

class ScanResultError(Exception):
    """Exception raised for errors in the scan results."""
    def __init__(self, message):
        super().__init__(message)

def format_sources_as_markdown(sources, aggregate_score):
    if not sources or aggregate_score == 0.0:
        markdown_string = "The content is free from plagiarism."
    else:
        markdown_string = f"The plagiarism check returned an aggregate score of {aggregate_score}%.\n\n"
        markdown_string += "Here are the sources it was copied from:\n"
        for index, source in enumerate(sources, start=1):
            markdown_string += f"{index}. [{source['title']}]({source['url']})\n"
    return markdown_string

def scan_and_wait_for_results(code, filename="run.txt", timeout=300):
  
    SCANNER_URL = os.getenv("SCANNER_URL")
    SCANNER_RESULTS_URL = os.getenv("SCANNER_RESULTS_URL")
    
    if not SCANNER_URL or not SCANNER_RESULTS_URL:
        logger.error("Missing SCANNER_URL or SCANNER_URL_KEY environment variables.")
        return None
    
    
    scan_url = SCANNER_URL
    results_url = SCANNER_RESULTS_URL

    # Data to send to the scan endpoint
    scan_data = {
        'text': code,
        'filename': filename
    }

    # Make the initial request to the scan endpoint
    response = requests.post(scan_url, json=scan_data)
    if response.status_code == 200:
        print("Scan initiated successfully.")
        scan_id = response.json().get('scan_id')
        print("Scan ID:", scan_id)
    else:
        print("Failed to initiate scan:", response.text)
        return None

    # Polling the results endpoint until a valid result is obtained or timeout
    start_time = time.time()
    while time.time() - start_time < timeout:
        result_response = requests.get(results_url + "/" + str(scan_id))
        if result_response.status_code == 200:
            result_data = result_response.json()
            if "results" in result_data:
                print("Results retrieved successfully:")
                final =  json.loads(result_data["results"]["result"])#['score']
                if 'error' in final:
                    raise ScanResultError(f"Error in scan results: {final['error']['message']}")
                
                return final["results"]
        time.sleep(5)  # wait for 5 seconds before next poll

    print("Failed to retrieve results within the timeout period.")
    return None

def run_check(user_prompt=None, ideal_response=None, checks={}):
    if ideal_response:
        res = scan_and_wait_for_results(ideal_response)
        score = "FAIL" if res["score"]['aggregatedScore'] > 30.0 else "PASS"
      
    elif user_prompt:
        res = scan_and_wait_for_results(user_prompt)
        score = "FAIL" if res["score"]['aggregatedScore'] > 30.0 else "PASS"
       
        
        
 #format other part of result
    formatted_output = format_sources_as_markdown(res["internet"], 
                                                  res["score"]['aggregatedScore'])
        
        
    check_result =  {
            "evaluation_result": score,
            "explanation_for_the_evaluation_result": formatted_output,
        }
    
    return check_result



class EvaluationPlagiarismChecker(LangChainBaseEvaluator):
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

        # happen here
        user_prompt_content = input_data.get("user_prompt", {}).get("content")
        ideal_response_content = input_data.get("alternative_last_ai_reply", {}).get("content")
        result = run_check(user_prompt=user_prompt_content, ideal_response=ideal_response_content, checks=config)
        
        
       

        return {"result":result}

