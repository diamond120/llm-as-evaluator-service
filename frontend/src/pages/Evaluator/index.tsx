import React, { useEffect, useState } from 'react';
import { Table, Space, Spin, Typography, Input, Button, Card } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import llm_evaluator_api_client from '../../services/llm_evaluator_api_client';
import { ApiError } from '../../components/api-error/api-error';

const { Title, Text } = Typography;
const { Search } = Input;

interface IEvaluators {
  key: string;
  name: string;
  description: string;
  evaluator_type: { name: string };
  evaluator_link?: string;
}

export default function EvaluatorList() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [evaluators, setEvaluators] = useState<IEvaluators[]>([]);
  const [filteredEvaluators, setFilteredEvaluators] = useState<IEvaluators[]>([]);
  const [filterOpts, setFilterOpts] = useState<{ text: string; value: string }[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [searchText, setSearchText] = useState('');

  useEffect(() => {
    fetchEvaluators();
  }, []);

  const fetchEvaluators = async () => {
    try {
      setLoading(true);
      const response = await llm_evaluator_api_client.fetchAllEvaluators(
        '',
        localStorage.getItem('token'),
      );
      const evaluatorsWithLink = response.map((e: IEvaluators) => ({
        ...e,
        key: e.name,
        evaluator_link: `/${e.name}`,
      }));
      setEvaluators(evaluatorsWithLink);
      setFilteredEvaluators(evaluatorsWithLink);
      setFilterOpts(
        [...new Set(response.map((e: IEvaluators) => e?.evaluator_type?.name))].map((e) => ({
          text: e,
          value: e,
        })),
      );
      setError(null);
    } catch (error) {
      setError(error as Error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchText(value);
    const filtered = evaluators.filter((evaluator) =>
      evaluator.name.toLowerCase().includes(value.toLowerCase()),
    );
    setFilteredEvaluators(filtered);
  };

  const handleCreateAndNavigate = async (evaluator_name: string) => {
    try {
      const newEvaluator = await llm_evaluator_api_client.createEvaluatorFromCopy(
        { src_evaluator_name: evaluator_name },
        localStorage.getItem('token'),
      );
      navigate(`/evaluators/${newEvaluator.evaluator_name}`);
    } catch (error) {
      console.error('Failed to create and navigate:', error);
    }
  };

  if (loading) return <Spin size="large" />;

  if (error) return <ApiError error={error} />;

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Evaluator Type',
      dataIndex: ['evaluator_type', 'name'],
      key: 'evaluator_type',
      filters: filterOpts,
      onFilter: (value: string, record: IEvaluators) => record.evaluator_type?.name.includes(value),
      render: (text: string) => <Text type="success">{text}</Text>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: IEvaluators) => (
        <Space size="middle">
          <Link to={`/evaluators${record.evaluator_link}`}>
            <Button type="primary" size="small">
              View
            </Button>
          </Link>
          <Button onClick={() => handleCreateAndNavigate(record.name)} size="small">
            Copy
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Search
          placeholder="Search evaluators by name"
          allowClear
          enterButton={<SearchOutlined />}
          size="large"
          onSearch={handleSearch}
          onChange={(e) => handleSearch(e.target.value)}
          style={{ width: 300 }}
        />
        <Table
          columns={columns}
          dataSource={filteredEvaluators}
          pagination={{ pageSize: 10 }}
          bordered
          title={() => <Text strong>{`Total ${filteredEvaluators.length} evaluators`}</Text>}
        />
      </Space>
    </Card>
  );
}
