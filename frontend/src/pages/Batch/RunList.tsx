import { SearchOutlined } from '@ant-design/icons';
import {
  Breadcrumb,
  Button,
  Card,
  Input,
  InputRef,
  Space,
  Spin,
  Table,
  TableColumnsType,
  TableProps,
  Typography,
} from 'antd';
import { Link } from 'react-router-dom';
import type { FilterDropdownProps } from 'antd/es/table/interface';
import qs from 'qs';
import { useEffect, useRef, useState } from 'react';
import Highlighter from 'react-highlight-words';
import { useLocation, useSearchParams } from 'react-router-dom';
import { ApiError } from '../../components/api-error/api-error';
import StatusTag from '../../components/status';
import { useAuth } from '../../context/AuthContext';
import llm_evaluator_api_client from '../../services/llm_evaluator_api_client';

type OnChange = NonNullable<TableProps<IEvaluations>['onChange']>;
type Filters = Parameters<OnChange>[1];

type GetSingle<T> = T extends (infer U)[] ? U : never;

interface IEvaluations {
  batch_name: string;
  name: string;
  id: number;
  run_id: number;
  evaluation_id: number;
  status: string;
  created_at: string;
}

const { Text } = Typography;

export default function RunList() {
  const { logout } = useAuth();
  const location = useLocation();
  const [filteredInfo, setFilteredInfo] = useState<Filters>({});
  const [loading, setLoading] = useState(true);
  const [evaluations, setEvaluations] = useState<IEvaluations[]>([]);
  const [filterOpts, setFilterOpts] = useState<{ text: string; value: string }[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [searchText, setSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const autoRefresh = searchParams.get('autoRefresh') === 'true' ? false : false;
  const [interValIds, setIntervalIds] = useState<number[]>([]);
  const [project, setProject] = useState('');
  const [engagementName, setEngagementName] = useState('');
  const [batchName, setBatchName] = useState('');

  const handleChange: OnChange = (pagination, filters, sorter) => {
    setFilteredInfo(filters);
  };

  const nextFetch = async () => {
    const filters = getFiltersFromSearchParams(searchParams);
    const queryString = qs.stringify(filters, { arrayFormat: 'comma' });
    const { result } = await llm_evaluator_api_client.fetchBatchRuns(
      queryString,
      localStorage.getItem('token'),
    );
    setProject(result.project);
    setBatchName(result.batch_name);
    setEngagementName(result.engagement);
    const evaluationsWithLink = updateLinkAndBatchInEvaluations(result);
    return evaluationsWithLink;
  };

  const getFiltersFromSearchParams = (searchParams: URLSearchParams) => {
    let filters: { [key: string]: string | string[] } = {};
    for (const [key, value] of searchParams.entries()) {
      if (filters[key]) {
        filters[key] = Array.isArray(filters[key])
          ? [...filters[key], value]
          : [filters[key], value];
      } else {
        filters[key] = value;
      }
    }
    return filters;
  };

  const clearFilters = () => {
    setFilteredInfo({});
    nextFetch();
    if (autoRefresh) {
      interValIds.forEach((i) => clearInterval(i));
      const intervalId = window.setInterval(nextFetch, 5000);
      setIntervalIds((prevIntervalIds) => [...prevIntervalIds, intervalId]);
    }
  };
  const handleSearch = (
    selectedKeys: string[],
    confirm: FilterDropdownProps['confirm'],
    dataIndex: keyof IEvaluations,
  ) => {
    confirm();
    setSearchText(selectedKeys[0]);
    setSearchedColumn(dataIndex);
  };

  const handleReset = (clearFilters: () => void) => {
    clearFilters();
    setSearchText('');
  };

  function updateLinkAndBatchInEvaluations(result: any) {
    console.log(`Result in Update: ${JSON.stringify(result)}`);
    const updatedResult = { ...result };
    updatedResult.runs = result.runs.map((run: any) => ({
      ...run,
      run_link: <a href={`/batches/evaluations/?run_id=${run.run_id}`}>view</a>,
    }));
    return updatedResult;
  }

  const firstFetch = async () => {
    try {
      setLoading(true);
      const evaluationsWithLink = await nextFetch();
      setEvaluations(evaluationsWithLink);
      const uniqueStatusValues = Array.from(
        new Set(evaluationsWithLink?.runs?.map((e) => e?.status)),
      );
      const filterOpts = uniqueStatusValues.map((status) => ({
        text: status || 'Unknown',
        value: status || 'Unknown',
      }));
      setFilterOpts(filterOpts);
      setError(null);
    } catch (error) {
      setError(error as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    firstFetch();
    interValIds.forEach((i) => clearInterval(i));
    if (autoRefresh) {
      const intervalId = window.setInterval(nextFetch, 5000);
      setIntervalIds((prevIntervalIds) => [...prevIntervalIds, intervalId]);
      return () => clearInterval(intervalId);
    }
  }, [location]);

  if (loading) return <Spin size="large" />;

  if (error) return <ApiError error={error} />;

  const columns: TableColumnsType<IEvaluations> = [
    {
      title: 'Run Id',
      dataIndex: 'run_id',
      key: 'run_id',
      ellipsis: true,
    },

    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      ellipsis: true,
      filters: filterOpts,
      filteredValue: filteredInfo.status || null,
      render: (text) => <StatusTag status={text} />,
      onFilter: (value, record) => record.status === value,
    },

    {
      title: 'View Evaluation',
      dataIndex: 'run_link',
      key: 'run_link',
      ellipsis: true,
    },
    {
      title: 'Created at',
      dataIndex: 'created_at',
      key: 'created_at',
      ellipsis: true,
      sorter: (a: any, b: any) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
  ];

  return (
    <div style={{ padding: '2px' }}>
      <Breadcrumb style={{ marginBottom: '16px' }}>
        <Breadcrumb.Item>
          <Link to="/">Home</Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          <Link to="/">Batches</Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>{batchName}</Breadcrumb.Item>
      </Breadcrumb>
      <Typography.Title level={2}>Run List</Typography.Title>
      <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
        <Card size="small">
          <Space direction="vertical">
            <Typography.Text>
              <strong>Engagement:</strong> {engagementName}
            </Typography.Text>
            <Typography.Text>
              <strong>Project:</strong> {project}
            </Typography.Text>
            <Typography.Text>
              <strong>Batch Name:</strong> {batchName}
            </Typography.Text>
          </Space>
        </Card>
        <Table
          columns={columns}
          dataSource={evaluations.runs}
          onChange={handleChange}
          scroll={{ x: 'max-content' }}
          pagination={{ pageSize: 50, showSizeChanger: true }}
          rowKey="run_id"
          bordered
          title={() => <Typography.Text strong>All Runs</Typography.Text>}
          footer={() => (
            <Typography.Text>Total {evaluations.runs?.length || 0} runs</Typography.Text>
          )}
        />
      </Space>
    </div>
  );
}
