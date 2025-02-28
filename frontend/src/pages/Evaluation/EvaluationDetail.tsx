import React from 'react';
import { Card, Collapse, Empty, Spin, Typography, Breadcrumb, Alert, Button, message } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import qs from 'qs';
import { useEffect, useState } from 'react';
import ReactJson from 'react-json-view';
import { useLocation, useSearchParams, Link } from 'react-router-dom';
import { ApiError } from '../../components/api-error/api-error';
import StatusTag from '../../components/status';
import llm_evaluator_api_client from '../../services/llm_evaluator_api_client';

const { Panel } = Collapse;
const { Title, Text } = Typography;

export default function EvaluationDetail() {
  const [loading, setLoading] = useState(true);
  const [evaluations, setEvaluations] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const [project, setProject] = useState('');
  const [engagementName, setEngagementName] = useState('');
  const [runStatus, setRunStatus] = useState('');
  const [batchName, setBatchName] = useState('');
  const [runId, setRunId] = useState('');
  const location = useLocation();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const filters = Object.fromEntries(searchParams.entries());
        const queryString = qs.stringify(filters, { arrayFormat: 'comma' });
        const { result } = await llm_evaluator_api_client.fetchBatchEvaluations(
          queryString,
          localStorage.getItem('token'),
        );
        setProject(result.project || 'N/A');
        setRunStatus(result.status || 'N/A');
        setEngagementName(result.engagement || 'N/A');
        setRunId(filters.run_id || 'N/A');
        setEvaluations(result.evaluations || []);

        // Set batch name from the first evaluation if available
        if (result.evaluations && result.evaluations.length > 0) {
          setBatchName(result.evaluations[0].batch_name || 'N/A');
        } else {
          setBatchName('N/A');
        }
      } catch (error) {
        setError(error instanceof Error ? error.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [searchParams]);

  const copyToClipboard = (text: string, fieldName: string) => {
    navigator.clipboard.writeText(text).then(
      () => {
        message.success(`${fieldName} copied to clipboard`);
      },
      (err) => {
        message.error('Failed to copy text');
        console.error('Could not copy text: ', err);
      },
    );
  };

  const renderJsonWithCopy = (data: any, fieldName: string) => {
    const jsonString = JSON.stringify(data, null, 2);
    return (
      <div>
        <Title
          level={5}
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          {fieldName}
          <Button
            icon={<CopyOutlined />}
            onClick={() => copyToClipboard(jsonString, fieldName)}
            size="small"
          >
            Copy Raw JSON
          </Button>
        </Title>
        <ReactJson
          src={data}
          enableClipboard={false}
          displayDataTypes={false}
          displayObjectSize={false}
          collapsed={3}
          theme="monokai"
        />
      </div>
    );
  };

  if (loading) return <Spin size="large" />;
  if (error) return <ApiError error={error} />;

  return (
    <div style={{ padding: '24px' }}>
      <Breadcrumb style={{ marginBottom: '16px' }}>
        <Breadcrumb.Item>
          <Link to="/">Home</Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          <Link to={`/evaluations?batch_name=${batchName}`}>{batchName}</Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          <Link to={`/batches/evaluations/?run_id=${runId}`}>Run {runId}</Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>Evaluations</Breadcrumb.Item>
      </Breadcrumb>

      <Title level={2}>Evaluation Details</Title>

      <Card style={{ marginBottom: '20px' }}>
        <Text strong>Engagement:</Text> {engagementName}
        <br />
        <Text strong>Project:</Text> {project}
        <br />
        <Text strong>Batch Name:</Text> {batchName}
        <br />
        <Text strong>Run Status:</Text> <StatusTag status={runStatus} />
      </Card>

      {evaluations.length > 0 ? (
        <Collapse accordion>
          {evaluations.map((evaluation: any, index: number) => (
            <Panel
              header={
                <span>
                  <Text strong>{evaluation.evaluation_name || `Evaluation ${index + 1}`}</Text> -
                  <Text type="secondary"> ID: {evaluation.evaluation_id || 'N/A'}</Text>
                </span>
              }
              key={index}
            >
              <Card>
                <p>
                  <Text strong>Evaluator Name:</Text>
                  {evaluation.evaluator_name ? (
                    <Link to={`/evaluators/${evaluation.evaluator_name}`}>
                      {evaluation.evaluator_name}
                    </Link>
                  ) : (
                    'N/A'
                  )}
                </p>
                <p>
                  <Text strong>Status:</Text> <StatusTag status={evaluation.status || 'N/A'} />
                </p>
                {evaluation.fail_reason && (
                  <Alert
                    message="Failure Reason"
                    description={
                      <pre
                        style={{
                          whiteSpace: 'pre-wrap',
                          wordWrap: 'break-word',
                          backgroundColor: '#f5f5f5',
                          padding: '10px',
                          borderRadius: '4px',
                          maxHeight: '200px',
                          overflowY: 'auto',
                        }}
                      >
                        {evaluation.fail_reason}
                      </pre>
                    }
                    type="error"
                    showIcon
                  />
                )}
                <p>
                  <Text strong>Created At:</Text> {evaluation.created_at || 'N/A'}
                </p>
                {renderJsonWithCopy(tryParseJSON(evaluation.message) || {}, 'Conversation')}
                {renderJsonWithCopy(evaluation.evaluation_config || {}, 'Evaluation Config')}
                {renderJsonWithCopy(evaluation.override_config || {}, 'Override Config')}
                {renderJsonWithCopy(tryParseJSON(evaluation.result) || {}, 'Result')}

                <p>
                  <Text strong>Input Tokens Used:</Text> {evaluation.input_tokens || 'N/A'}
                </p>
                <p>
                  <Text strong>Output Tokens Used:</Text> {evaluation.output_tokens || 'N/A'}
                </p>
              </Card>
            </Panel>
          ))}
        </Collapse>
      ) : (
        <Empty
          description={<span>No evaluation data available</span>}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}
    </div>
  );
}

// Helper function to safely parse JSON
function tryParseJSON(jsonString: string) {
  try {
    return JSON.parse(jsonString);
  } catch (e) {
    return null;
  }
}
