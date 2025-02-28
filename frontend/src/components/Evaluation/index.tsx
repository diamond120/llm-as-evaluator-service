import { Card, Spin, Descriptions } from 'antd';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router';
import llm_evaluator_api_client from '../../services/llm_evaluator_api_client';
import { useErrorBoundary } from 'react-error-boundary';
import { ApiError, ErrorData } from '../api-error/api-error';
import { JsonTree } from 'react-editable-json-tree';
import StatusTag from '../status';
const { Item } = Descriptions;

export default function Evaluation() {
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { evaluationId } = useParams();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await llm_evaluator_api_client.fetchEvaluationById(
          evaluationId,
          localStorage.getItem('token'),
        );
        setEvaluation(response);
        setError(null);
      } catch (error) {
        setError(error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []); // Empty dependency array means this effect runs only once, when the component mounts

  if (loading) return <Spin />;

  if (error) return <ApiError error={error as ErrorData} />;

  return (
    <Card title={`Evalution: ${evaluation.name}`}>
      <Descriptions bordered column={1}>
        <Item label="Name">{evaluation.name}</Item>
        <Item label="Id">{evaluation.id}</Item>
        <Item label="Run Id">{evaluation.run_id}</Item>
        <Item label="Evaluation Id">{evaluation.evaluation_id}</Item>
        <Item label="Status">
          <StatusTag status={evaluation.status} />
        </Item>
        <Item label="Output">
          <JsonTree data={evaluation.output || {}} readonly={true} />
        </Item>
        <Item label="Prompt Tokens Used">{evaluation.prompt_tokens_used}</Item>
        <Item label="Generate Tokens Used:">{evaluation.generate_tokens_used}</Item>
        <Item label="Is agregator">{evaluation.is_agregator}</Item>
        <Item label="Is Used For Agregation">{evaluation.is_used_for_agregation}</Item>
        <Item label="Fail Reason">{evaluation.fail_reason}</Item>
        <Item label="Is Dev">{evaluation.is_dev}</Item>
        <Item label="Evaluator Config Override">
          <JsonTree data={evaluation.evaluator_config_override || {}} readonly />
        </Item>
      </Descriptions>
    </Card>
  );
}
