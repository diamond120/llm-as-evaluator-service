import * as Sentry from '@sentry/react';
import { config } from './config';

export function bootstrap() {
  const dsn = config.sentryDSN;

  if (!dsn) {
    console.warn('No DSN has been defined. Skipping Sentry configuration');

    return;
  }

  Sentry.init({
    dsn,
    enableTracing: false,
    integrations: [
      Sentry.feedbackIntegration({
        colorScheme: 'dark',
      }),
    ],
  });
}

export default Sentry;
