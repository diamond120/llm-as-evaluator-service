declare global {
  interface Window {
    env?: Partial<{
      VITE_API_HOST: string;
      VITE_GOOGLE_CLIENT_ID: string;
      VITE_SENTRY_DSN: string;
      VITE_REVIEW_FORM_URL: string;
      VITE_REVIEW_FORM_TASK_URL_ENTRY_ID: string;
      VITE_REVIEW_FORM_AUTHOR_EMAIL_ENTRY_ID: string;
      VITE_DEFAULT_METADATA_KEYS: string;
      LLM_EVALUATOR_API_BASE_URL: string;
    }>;
  }
}

class Configuration {
  get apiUrl(): string {
    return (
      window.env?.VITE_API_HOST ??
      (import.meta.env.VITE_API_HOST || 'http://localhost:8887/api')
    );
  }

  get evaluatorBaseUrl(): string {
    return (
      window.env?.LLM_EVALUATOR_API_BASE_URL ??
      (import.meta.env.LLM_EVALUATOR_API_BASE_URL ||
        'http://localhost:8887/api/v1/e')
    );
  }

  get sentryDSN(): string | undefined {
    return window.env?.VITE_SENTRY_DSN ?? (import.meta.env.VITE_SENTRY_DSN || 'default sentry');
  }

  get llmEvaluatorBaseUrl(): string {
    return process.env.LLM_EVALUATOR_API_BASE_URL;
  }
}

export const config = new Configuration();
