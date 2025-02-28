import { FormBuilder } from '@ginkgo-bioworks/react-json-schema-form-builder';
import { Button, Card, Form, Input, Select, Space, Spin, Typography, notification } from 'antd';
import { useEffect, useState } from 'react';
import { createUseStyles } from 'react-jss';
import { useNavigate } from 'react-router-dom';
import llm_evaluator_api_client from '../../services/llm_evaluator_api_client';
import { ApiError } from '../api-error/api-error';

const { TextArea } = Input;

const useStyles = createUseStyles({
  myBackground: {
    background: '#fff',
    '& div': {
      // background: '#fff',
      'border-color': 'lightgrey',
    },
  },
});

export default function CreateEvaluator() {
  const classes = useStyles();
  const [form] = Form.useForm();
  const [evaluatorTypes, setEvaluatorTypes] = useState(null);
  const [outputSchema, setOutputSchema] = useState(
    '{"title": "Output Schema", "description": "Create Output Schema"}',
  );
  const [uioutputschema, setUiOutputSchema] = useState('{}');
  const [inputSchema, setInputSchema] = useState(
    '{"title": "Input Schema", "description": "Create Input Schema"}',
  );
  const [uiinputschema, setUiInputSchema] = useState('{}');
  const [showFormBuilderForInputSchema, setShowFormBuilderForInputSchema] = useState(false);
  const [showFormBuilderForOutputSchema, setShowFormBuilderForOutputSchema] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const createEvaluatorTypesOptions = (evaluatorTypes) => {
    return evaluatorTypes.map((e) => {
      return {
        value: e.id,
        label: <span>{e.name}</span>,
      };
    });
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await llm_evaluator_api_client.fetchAllEvaluatorTypes(
          localStorage.getItem('token'),
        );
        setEvaluatorTypes(createEvaluatorTypesOptions(response));
        setError(null);
      } catch (error) {
        setError(error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <Spin />;

  if (error) return <ApiError error={error as ErrorData} />;

  const getJsonSchema = (schema) => {
    const { title, description, ...cleanedSchema } = schema;
    return cleanedSchema;
  };

  const parseJsonSafe = (jsonString) => {
    try {
      return JSON.parse(jsonString);
    } catch (error) {
      console.error('Error parsing JSON:', error);
      return null;
    }
  };

  const handleToggleForInputSchema = () => {
    setShowFormBuilderForInputSchema(!showFormBuilderForInputSchema);
  };
  const handleToggleForOutputSchema = () => {
    setShowFormBuilderForOutputSchema(!showFormBuilderForOutputSchema);
  };

  const handleInputSchemaChange = (e: Event) => {
    setInputSchema(e?.target?.value);
  };
  const handleOutputSchemaChange = (e) => {
    setOutputSchema(e.target.value);
  };
  const handleSubmit = async () => {
    try {
      const { temperature, seed, max_tokens, evaluatorConfig, ...rest } = form.getFieldsValue();
      const temperatureInt = temperature ? parseInt(temperature, 10) : 0;
      const seedInt = seed ? parseInt(seed, 10) : null;
      const maxTokensInt = max_tokens ? parseInt(max_tokens, 10) : 1000;
      const outputSchemaObj = parseJsonSafe(outputSchema);
      const inputSchemaObj = parseJsonSafe(inputSchema);
      //const configSchemaObj = parseJsonSafe(configSchema);

      if (!outputSchemaObj || !inputSchemaObj) {
        throw new Error('Invalid JSON schema');
      }

      const payload = {
        ...rest,
        output_schema: outputSchemaObj,
        input_schema: inputSchemaObj,
        config: parseJsonSafe(evaluatorConfig),
        llm_params: { temperature: temperatureInt, seed: seedInt, max_tokens: maxTokensInt },
      };
      const response = await llm_evaluator_api_client.createEvaluator(
        payload,
        localStorage.getItem('token'),
      );
      notification.open({
        message: 'Successfully Created',
        duration: 1,
      });
      navigate('/evaluators');
    } catch (error) {
      console.error('Error while processing payload:', error);
      setError(error);
    }
  };
  return (
    <>
      <Form
        labelCol={{
          span: 6,
        }}
        wrapperCol={{
          span: 18,
        }}
        form={form}
        name="create_evaluators_form"
        style={{
          width: '100%',
        }}
        autoComplete="off"
        initialValues={{
          llm_params: [{}],
          input_schema: [{}],
          output_schema: [{}],
          config: {},
        }}
      >
        <Card size="small" title={`Evaluator Details`} key={'evaluator_details'}>
          <Form.Item label="Name" name="name">
            <Input required />
          </Form.Item>
          <Form.Item label="Description" name="description">
            <Input required />
          </Form.Item>
          <Typography.Title level={4}>LLM Config</Typography.Title>
          <Form.Item label="LLM Provider" name="llm_provider">
            <Select
              options={[
                {
                  value: 'openai_api',
                  label: <span>Openai API</span>,
                },
                {
                  value: 'groq_api',
                  label: <span>Groq API</span>,
                },
              ]}
              required
            />
          </Form.Item>
          <Form.Item label="LLM Model" name="llm_model">
            <Input required />
          </Form.Item>
          <Typography.Title level={4}>LLM Params</Typography.Title>
          <Form.Item label="Temperature" name="temperature">
            <Input type="number" required />
          </Form.Item>

          <Form.Item label="Seed" name="seed">
            <Input type="number" required />
          </Form.Item>

          <Form.Item label="Max Tokens" name="max_tokens">
            <Input type="number" required />
          </Form.Item>

          <Form.Item label="Evaluator Type" name="evaluator_type_id">
            <Select options={evaluatorTypes} required />
          </Form.Item>
          <Typography.Title level={4}>Evaluator Config</Typography.Title>
          <Form.Item label="Config" name="evaluatorConfig">
            <TextArea rows={4} required />
          </Form.Item>
          <Space direction="vertical" style={{ margin: '20px', width: '98%' }}>
            <Button onClick={handleToggleForOutputSchema} ghost type={'primary'}>
              {showFormBuilderForOutputSchema ? 'Use Input' : 'Use Form Builder For Output Schema'}
            </Button>
            {showFormBuilderForOutputSchema ? (
              <FormBuilder
                schema={outputSchema}
                uischema={uioutputschema}
                onChange={(newSchema, newUiSchema) => {
                  setOutputSchema(newSchema);
                  setUiOutputSchema(newUiSchema);
                }}
                className={classes.myBackground}
              />
            ) : (
              <TextArea
                rows={4}
                placeholder="Enter the entire output schema object"
                onChange={handleOutputSchemaChange}
              />
            )}

            <Button onClick={handleToggleForInputSchema} ghost type={'primary'}>
              {showFormBuilderForInputSchema ? 'Use Input' : 'Use Form Builder For Input Schema'}
            </Button>
            {showFormBuilderForInputSchema ? (
              <FormBuilder
                schema={inputSchema}
                uischema={uiinputschema}
                onChange={(newSchema, newUiSchema) => {
                  setInputSchema(newSchema);
                  setUiInputSchema(newUiSchema);
                }}
                className={classes.myBackground}
              />
            ) : (
              <TextArea
                rows={4}
                placeholder="Enter the entire input schema object"
                onChange={handleInputSchemaChange}
              />
            )}
          </Space>
        </Card>
        <Space direction="vertical" size={150} style={{ display: 'flex' }}></Space>
      </Form>

      <Space style={{ marginTop: 16 }}>
        <Button type="primary" onClick={handleSubmit}>
          Submit
        </Button>
      </Space>
    </>
  );
}
