import React from 'react';
import { Input, Typography, Card } from 'antd';
import { JsonTree } from 'react-editable-json-tree';

const { TextArea } = Input;
const { Title } = Typography;

export default function EvaluatorConfig({ configField, evaluator, setEvaluator }) {
  const isString = typeof evaluator.config[configField] === 'string';

  const handleChange = (value) => {
    setEvaluator({
      ...evaluator,
      config: {
        ...evaluator.config,
        [configField]: value,
      },
    });
  };

  return (
    <Card title={<Title level={4}>{configField}</Title>} style={{ marginBottom: 16 }}>
      {isString ? (
        <TextArea
          onChange={(e) => handleChange(e.target.value)}
          style={{ whiteSpace: 'pre-wrap', width: '100%' }}
          value={evaluator.config[configField]}
          rows={Math.max(3, Math.min(10, evaluator.config[configField].split('\n').length))}
          autoSize={{ minRows: 3, maxRows: 10 }}
        />
      ) : (
        <JsonTree
          data={evaluator.config[configField]}
          onFullyUpdate={(e) => handleChange(JSON.parse(e))}
        />
      )}
    </Card>
  );
}
