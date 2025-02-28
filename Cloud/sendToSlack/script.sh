gcloud functions deploy sendToSlack \
--runtime python310 \
--trigger-topic llm-evaluator-alerts \
--entry-point publish_to_slack \
--region us-central1 \
--set-secrets SLACK_TOKEN=llm-slack-webhook:latest \
--service-account llm-evaluator-sa@xxxx-gpt.iam.gserviceaccount.com \
--project xxxx-gpt \
--set-env-vars CHANNEL_ID=C079TALD6Q0 \
--retry
