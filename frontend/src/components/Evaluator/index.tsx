import React, { useContext, useEffect, useState } from 'react';
import { SaveOutlined } from '@ant-design/icons';
import {
  Button,
  Card,
  Spin,
  Typography,
  notification,
  Space,
  Tabs,
  Form,
  Input,
  InputNumber,
} from 'antd';
import { useParams, Link, useNavigate } from 'react-router-dom';
import llm_evaluator_api_client from '../../services/llm_evaluator_api_client';
import { ApiError, ErrorData } from '../api-error/api-error';
import AceEditor from 'react-ace';
import 'ace-builds/src-noconflict/mode-json';
import 'ace-builds/src-noconflict/theme-github';
import AuthContext from '../../context/AuthContext';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const formatJsonWithNewlines = (obj) => {
  return JSON.stringify(
    obj,
    (key, value) => {
      if (typeof value === 'string') {
        return value.replace(/\n/g, '\\n');
      }
      return value;
    },
    2,
  ).replace(/\\n/g, '\n');
};

const parseJsonWithNewlines = (jsonString) => {
  return JSON.parse(jsonString.replace(/\n(?=(?:[^"]*"[^"]*")*[^"]*$)/g, '\\n'));
};

const JsonEditor = ({ value, onChange, title }) => {
  const [error, setError] = useState(null);

  const handleChange = (newValue) => {
    try {
      JSON.parse(newValue); // Check if it's valid JSON
      setError(null);
      onChange(newValue);
    } catch (err) {
      setError('Invalid JSON: ' + err.message);
    }
  };

  return (
    <Card title={title} style={{ marginBottom: 16 }}>
      <AceEditor
        mode="json"
        theme="github"
        onChange={handleChange}
        value={value}
        name={`editor-${title}`}
        editorProps={{ $blockScrolling: true }}
        setOptions={{
          useWorker: false,
          showLineNumbers: true,
          tabSize: 2,
          wrap: true,
        }}
        style={{ width: '100%', height: '500px' }}
      />
      {error && <Text type="danger">{error}</Text>}
    </Card>
  );
};

export default function Evaluator() {
  const [evaluator, setEvaluator] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { evaluatorName } = useParams();
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const { user } = useContext(AuthContext);
  const isSuperAdmin = user && user.access === 'superadmin';

  useEffect(() => {
    const fetchData = async () => {
      if (!evaluatorName) {
        setError(new Error('Evaluator name is missing'));
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await llm_evaluator_api_client.fetchEvaluatorByName(
          evaluatorName,
          localStorage.getItem('token'),
        );
        setEvaluator(response);
        form.setFieldsValue({
          name: response.name,
          description: response.description,
          llm_provider: response.llm_provider,
          llm_model: response.llm_model,
          ...response.llm_params,
        });
        setError(null);
      } catch (error) {
        setError(error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [evaluatorName, form]);

  const handleFormChange = (changedValues, allValues) => {
    setEvaluator((prev) => ({
      ...prev,
      ...changedValues,
      llm_params: {
        temperature: allValues.temperature,
        seed: allValues.seed,
        max_tokens: allValues.max_tokens,
      },
    }));
  };

  const handleConfigChange = (newValue) => {
    try {
      const parsed = JSON.parse(newValue);
      setEvaluator((prev) => ({
        ...prev,
        config: parsed,
      }));
    } catch (err) {
      // If it's not valid JSON, don't update the state
      console.error('Invalid JSON:', err);
    }
  };

  const handleSchemaChange = (schemaType, newValue) => {
    try {
      const parsed = JSON.parse(newValue);
      setEvaluator((prev) => ({
        ...prev,
        [schemaType]: parsed,
      }));
    } catch (err) {
      // If it's not valid JSON, don't update the state
      console.error('Invalid JSON:', err);
    }
  };

  const handleSubmit = async () => {
    if (!isSuperAdmin) {
      notification.error({
        message: 'Permission Denied',
        description: "You don't have access to modify evaluators.",
        duration: 3,
      });
      return;
    }

    try {
      const values = await form.validateFields();
      const updatedEvaluator = {
        ...evaluator,
        ...values,
        llm_params: {
          temperature: values.temperature,
          seeds: values.seeds,
          max_tokens: values.max_tokens,
        },
      };
      const response = await llm_evaluator_api_client.updateEvaluator(
        updatedEvaluator.id,
        updatedEvaluator,
        localStorage.getItem('token'),
      );
      console.log('PUT request successful:', response.data);
      notification.success({
        message: 'Successfully Updated',
        duration: 3,
      });
    } catch (error) {
      console.error('Error while making PUT request:', error);
      notification.error({
        message: 'Update Failed',
        description: 'An error occurred while updating the evaluator.',
        duration: 3,
      });
    }
  };

  if (loading) return <Spin size="large" />;

  if (error) {
    return (
      <Result
        status="error"
        title="Failed to load evaluator"
        subTitle={error.message || 'An unknown error occurred'}
        extra={[
          <Button type="primary" key="goBack" onClick={() => navigate('/evaluators')}>
            Go Back to Evaluators List
          </Button>,
        ]}
      />
    );
  }

  if (!evaluator) {
    return (
      <Result
        status="404"
        title="404"
        subTitle="Sorry, the evaluator you're looking for does not exist."
        extra={
          <Button type="primary" onClick={() => navigate('/evaluators')}>
            Back to Evaluators List
          </Button>
        }
      />
    );
  }

  return (
    <Card title={<Title level={2}>{`Evaluator: ${evaluator.name}`}</Title>}>
      <Form form={form} onValuesChange={handleFormChange} layout="vertical">
        <Tabs defaultActiveKey="1">
          <TabPane tab="Basic Information" key="1">
            <Form.Item name="name" label="Name" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="description" label="Description" rules={[{ required: true }]}>
              <Input.TextArea rows={4} />
            </Form.Item>
          </TabPane>
          <TabPane tab="LLM Parameters" key="2">
            <Form.Item name="llm_provider" label="LLM Provider" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="llm_model" label="LLM Model" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item
              name="temperature"
              label="Temperature"
              rules={[{ required: false, type: 'number' }]}
            >
              <InputNumber min={0} max={1} step={0.1} />
            </Form.Item>
            <Form.Item name="seed" label="Seed" rules={[{ required: false, type: 'number' }]}>
              <InputNumber min={1} />
            </Form.Item>
            <Form.Item
              name="max_tokens"
              label="Max Tokens"
              rules={[{ required: false, type: 'number' }]}
            >
              <InputNumber min={1} />
            </Form.Item>
          </TabPane>
          <TabPane tab="Evaluator Configuration" key="3">
            <JsonEditor
              value={JSON.stringify(evaluator.config, null, 2)}
              onChange={handleConfigChange}
              title="Evaluator Configuration"
            />
          </TabPane>
          <TabPane tab="Schemas" key="4">
            <Tabs defaultActiveKey="input">
              <TabPane tab="Input Schema" key="input">
                <JsonEditor
                  value={JSON.stringify(evaluator.input_schema, null, 2)}
                  onChange={(newValue) => handleSchemaChange('input_schema', newValue)}
                  title="Input Schema"
                />
              </TabPane>
              <TabPane tab="Output Schema" key="output">
                <JsonEditor
                  value={JSON.stringify(evaluator.output_schema, null, 2)}
                  onChange={(newValue) => handleSchemaChange('output_schema', newValue)}
                  title="Output Schema"
                />
              </TabPane>
            </Tabs>
          </TabPane>
        </Tabs>
        <Space style={{ marginTop: 16 }}>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSubmit}>
            Save Changes
          </Button>
          <Link to="/evaluators">
            <Button>Back to Evaluators</Button>
          </Link>
        </Space>
      </Form>
    </Card>
  );
}
