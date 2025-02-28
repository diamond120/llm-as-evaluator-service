import React, { useState, useEffect, useContext } from 'react';
import { Select, DatePicker, Card, Table, Statistic, Row, Col, message } from 'antd';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import llm_evaluator_api_client from '../services/llm_evaluator_api_client';
import AuthContext from '../context/AuthContext';

const { Option } = Select;
const { RangePicker } = DatePicker;

const TokenUsageDashboard = () => {
  const { user } = useContext(AuthContext);
  const token = localStorage.getItem('token');
  const [engagement, setEngagement] = useState(null);
  const [engagements, setEngagements] = useState([]);
  const [project, setProject] = useState(null);
  const [projects, setProjects] = useState([]);
  const [dateRange, setDateRange] = useState([]);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState({
    engagements: false,
    projects: false,
    data: false,
  });

  useEffect(() => {
    fetchEngagements();
  }, []);

  useEffect(() => {
    if (engagement) {
      fetchProjects(engagement);
    }
  }, [engagement]);

  useEffect(() => {
    if (engagement && dateRange.length === 2) {
      fetchTokenUsageData();
    }
  }, [engagement, project, dateRange]);

  const fetchEngagements = async () => {
    setLoading((prev) => ({ ...prev, engagements: true }));
    try {
      const response = await llm_evaluator_api_client.getAllEngagements(token);
      setEngagements(response.data);
    } catch (error) {
      notification.error({ message: 'Error fetching engagements' });
    } finally {
      setLoading((prev) => ({ ...prev, engagements: false }));
    }
  };

  const fetchProjects = async (engagementId) => {
    setLoading((prev) => ({ ...prev, projects: true }));
    try {
      const response = await llm_evaluator_api_client.getProjectsForEngagement(engagementId, token);
      setProjects(response.data);
      setProject(null); // Reset project selection when engagement changes
    } catch (error) {
      notification.error({ message: 'Failed to load projects' });
      console.error('Error fetching projects:', error);
    } finally {
      setLoading((prev) => ({ ...prev, projects: false }));
    }
  };

  const fetchTokenUsageData = async () => {
    setLoading((prev) => ({ ...prev, data: true }));
    try {
      const startDate = dateRange[0].format('YYYY-MM-DD');
      const endDate = dateRange[1].format('YYYY-MM-DD');
      const response = await llm_evaluator_api_client.getTokenUsageData(
        engagement,
        startDate,
        endDate,
        project,
        token,
      );
      if (response.status !== 200) {
        throw new Error('Failed to fetch token usage data');
      }
      const aggregatedData = aggregateDataByDay(response.data);
      setData(aggregatedData);
    } catch (error) {
      notification.error({ message: 'Failed to load token usage data' });
      console.error('Error fetching token usage data:', error);
    } finally {
      setLoading((prev) => ({ ...prev, data: false }));
    }
  };

  const aggregateDataByDay = (data) => {
    const aggregated = data.reduce((acc, item) => {
      const key = `${item.date}-${item.provider}-${item.model}`;
      if (!acc[key]) {
        acc[key] = { ...item };
      } else {
        acc[key].inputTokens += item.inputTokens;
        acc[key].outputTokens += item.outputTokens;
        acc[key].totalCost += item.totalCost;
      }
      return acc;
    }, {});
    return Object.values(aggregated);
  };

  const columns = [
    {
      title: 'Date',
      dataIndex: 'date',
      key: 'date',
    },
    {
      title: 'Provider',
      dataIndex: 'provider',
      key: 'provider',
    },
    {
      title: 'Model',
      dataIndex: 'model',
      key: 'model',
    },
    {
      title: 'Input Tokens',
      dataIndex: 'inputTokens',
      key: 'inputTokens',
    },
    {
      title: 'Output Tokens',
      dataIndex: 'outputTokens',
      key: 'outputTokens',
    },
    {
      title: 'Total Cost',
      dataIndex: 'totalCost',
      key: 'totalCost',
      render: (text) => `$${parseFloat(text).toFixed(2)}`,
    },
  ];

  const totalCost = data.reduce((sum, item) => sum + item.totalCost, 0);
  const totalTokens = data.reduce((sum, item) => sum + item.inputTokens + item.outputTokens, 0);

  const providerCosts = data.reduce((acc, item) => {
    acc[item.provider] = (acc[item.provider] || 0) + item.totalCost;
    return acc;
  }, {});

  const modelCosts = data.reduce((acc, item) => {
    acc[item.model] = (acc[item.model] || 0) + item.totalCost;
    return acc;
  }, {});

  const providerCostData = Object.entries(providerCosts).map(([provider, cost]) => ({
    provider,
    cost,
  }));
  const modelCostData = Object.entries(modelCosts).map(([model, cost]) => ({ model, cost }));

  return (
    <div style={{ padding: '20px' }}>
      <Row gutter={16} style={{ marginBottom: '20px' }}>
        <Col span={8}>
          <Select
            style={{ width: '100%' }}
            placeholder="Select an engagement"
            onChange={(value) => setEngagement(value)}
            loading={loading.engagements}
            disabled={loading.engagements}
          >
            {engagements.map((eng) => (
              <Option key={eng.id} value={eng.id}>
                {eng.name}
              </Option>
            ))}
          </Select>
        </Col>
        <Col span={8}>
          <Select
            style={{ width: '100%' }}
            placeholder="Select a project"
            onChange={(value) => setProject(value)}
            loading={loading.projects}
            disabled={!engagement || loading.projects}
          >
            <Option key="all" value={null}>
              All Projects
            </Option>
            {projects.map((proj) => (
              <Option key={proj.id} value={proj.id}>
                {proj.name}
              </Option>
            ))}
          </Select>
        </Col>
        <Col span={8}>
          <RangePicker
            style={{ width: '100%' }}
            onChange={(dates) => setDateRange(dates)}
            disabled={!engagement}
          />
        </Col>
      </Row>

      {data.length > 0 && (
        <>
          <Row gutter={16} style={{ marginBottom: '20px' }}>
            <Col span={12}>
              <Card>
                <Statistic title="Total Cost" value={totalCost} precision={2} prefix="$" />
              </Card>
            </Col>
            <Col span={12}>
              <Card>
                <Statistic title="Total Tokens Used" value={totalTokens} precision={0} />
              </Card>
            </Col>
          </Row>

          <Card title="Daily Token Usage" style={{ marginBottom: '20px' }}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="inputTokens"
                  stroke="#8884d8"
                  name="Input Tokens"
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="outputTokens"
                  stroke="#82ca9d"
                  name="Output Tokens"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="totalCost"
                  stroke="#ffc658"
                  name="Total Cost"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Row gutter={16} style={{ marginBottom: '20px' }}>
            <Col span={12}>
              <Card title="Cost by Provider">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={providerCostData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="provider" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="cost" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </Col>
            <Col span={12}>
              <Card title="Cost by Model">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={modelCostData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="model" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="cost" fill="#82ca9d" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </Col>
          </Row>

          <Card title="Detailed Usage Data">
            <Table columns={columns} dataSource={data} />
          </Card>
        </>
      )}
    </div>
  );
};

export default TokenUsageDashboard;
