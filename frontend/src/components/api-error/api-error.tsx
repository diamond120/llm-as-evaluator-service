import { Alert } from "antd";

export type ErrorData =
  | {
      message: string;
    }
  | {
      data: {
        message: string;
      };
    }
  | {
      error: string;
    };

export interface ApiErrorProps {
  error: ErrorData;
}
export function ApiError({ error }: ApiErrorProps) {
  console.log(error, "********************************");
  const message =
    'data' in error
      ? error.data?.message
      : 'message' in error
      ? error.message
      : error.error;

  return (
    <Alert
    message="Something went wrong"
    description={message}
    type="error"
    closable
  />
  );
}
