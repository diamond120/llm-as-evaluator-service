import { useEffect, useState, useRef } from 'react';
import { Form, Input, InputRef, Spin, TableColumnsType, TableProps, Typography } from 'antd';
import { Button, Space, Table } from 'antd';
import llm_evaluator_api_client from '../../services/llm_evaluator_api_client';
import { ApiError, ErrorData } from '../api-error/api-error';
import { SearchOutlined } from '@ant-design/icons';
import { config } from '../../services/config';
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { JsonTree } from 'react-editable-json-tree';
import StatusTag from '../status';
import qs from 'qs';
import type { FilterDropdownProps } from 'antd/es/table/interface';
import Highlighter from 'react-highlight-words';
import { useAuth } from '../../context/AuthContext';

type OnChange = NonNullable<TableProps<IEvaluations>['onChange']>;
type Filters = Parameters<OnChange>[1];

type GetSingle<T> = T extends (infer U)[] ? U : never;
type Sorts = GetSingle<Parameters<OnChange>[2]>;

type FieldType = {
  batchName?: string;
};

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

export default function EvaluationsList() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [filteredInfo, setFilteredInfo] = useState<Filters>({});
  const [loading, setLoading] = useState(true);
  const [evaluations, setEvaluations] = useState(null);
  const [filterOpts, setFilterOpts] = useState(null);
  const [error, setError] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const autoRefresh = searchParams.get('autoRefresh') === 'true' ? false : false;
  const [interValIds, setIntervalIds] = useState([]);

  const handleChange: OnChange = async (pagination, filters, sorter) => {
    try {
      if (autoRefresh) {
        interValIds.forEach((i) => clearInterval(i));
        setIntervalIds([]);
        const intervalId = setInterval(nextFetchWithFilters, 5000, filters);
        setIntervalIds((prevIntervalIds) => [...prevIntervalIds, intervalId]);
      }
      await nextFetchWithFilters(filters);
    } catch (error) {
      setError(error);
    }
  };

  const nextFetchWithFilters = async (filters) => {
    setFilteredInfo(filters);
    const queryParams = qs.stringify(filters, { arrayFormat: 'comma' });
    const { result } = await llm_evaluator_api_client.fetchBatchRuns(
      queryParams,
      localStorage.getItem('token'),
    );
    const evaluationsWithLink = updateLinkAndBatchInEvaluations(result);
    setEvaluations(evaluationsWithLink);
  };

  const nextFetch = async () => {
    const filters = getFiltersFromSearchParams(searchParams);
    const queryString = qs.stringify(filters, { arrayFormat: 'comma' });
    const { result } = await llm_evaluator_api_client.fetchBatchRuns(
      queryString,
      localStorage.getItem('token'),
    );
    const evaluationsWithLink = updateLinkAndBatchInEvaluations(result);
    return evaluationsWithLink;
  };

  const getFiltersFromSearchParams = (searchParams) => {
    let filters = {};
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
      const intervalId = setInterval(nextFetch, 5000);
      setIntervalIds((prevIntervalIds) => [...prevIntervalIds, intervalId]);
    }
  };
  const handleSearch = (
    selectedKeys: string[],
    confirm: FilterDropdownProps['confirm'],
    dataIndex: DataIndex,
  ) => {
    confirm();
    setSearchText(selectedKeys[0]);
    setSearchedColumn(dataIndex);
  };

  const handleReset = (clearFilters: () => void) => {
    clearFilters();
    setSearchText('');
  };
  const getColumnSearchProps = (dataIndex: DataIndex): TableColumnType<IEvaluations> => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
      <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
        <Input
          ref={searchInput}
          placeholder={`Search ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => handleSearch(selectedKeys as string[], confirm, dataIndex)}
          style={{ marginBottom: 8, display: 'block' }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => handleSearch(selectedKeys as string[], confirm, dataIndex)}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            Search
          </Button>
          <Button
            onClick={() => clearFilters && handleReset(clearFilters)}
            size="small"
            style={{ width: 90 }}
          >
            Reset
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => {
              confirm({ closeDropdown: false });
              setSearchText((selectedKeys as string[])[0]);
              setSearchedColumn(dataIndex);
            }}
          >
            Filter
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => {
              close();
            }}
          >
            close
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
    ),
    onFilter: (value, record) =>
      record[dataIndex]
        .toString()
        .toLowerCase()
        .includes((value as string).toLowerCase()),
    onFilterDropdownOpenChange: (visible) => {
      if (visible) {
        setTimeout(() => searchInput.current?.select(), 100);
      }
    },
    render: (text) =>
      searchedColumn === dataIndex ? (
        <Highlighter
          highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
          searchWords={[searchText]}
          autoEscape
          textToHighlight={text ? text.toString() : ''}
        />
      ) : (
        text
      ),
  });

  function updateLinkAndBatchInEvaluations(result: any) {
    //console.log(`Result in Update: ${JSON.stringify(result)}`);
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
        new Set(evaluationsWithLink.runs.map((e) => e?.status)),
      );
      const filterOpts = uniqueStatusValues.map((status) => ({
        text: status || 'Unknown',
        value: status || 'Unknown',
      }));
      setFilterOpts(filterOpts);
      setError(null);
    } catch (error) {
      setError(error);
    } finally {
      setLoading(false);
    }
  };
  // async function nextFetch() {
  //   const queryParams = qs.stringify(filters, { arrayFormat: 'comma' });
  //   const { result } = await llm_evaluator_api_client.fetchBatchEvaluations(queryParams);
  //   const evaluationsWithLink = updateLinkAndBatchInEvaluations(result);
  //   setEvaluations(evaluationsWithLink);
  //   return evaluationsWithLink;
  // }
  useEffect(() => {
    firstFetch();
    interValIds.forEach((i) => clearInterval(i));
    if (autoRefresh) {
      const intervalId = setInterval(nextFetch, 5000);
      setIntervalIds((prevIntervalIds) => [...prevIntervalIds, intervalId]);
      return () => clearInterval(intervalId);
    }
  }, [location]);

  if (loading) return <Spin />;

  if (error) return <ApiError error={error as ErrorData} />;

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
      onFilter: (value, record) => record.status.indexOf(value as string) === 0,
    },

    {
      title: 'View Evaluation',
      dataIndex: 'run_link',
      key: 'run_link',
      ellipsis: true,
    },
  ];

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Button onClick={clearFilters}>Clear filter</Button>
        <Button onClick={logout}>Logout</Button>
      </Space>
      <Typography.Title level={5}>
        Engagement: <Text mark>{evaluations?.engagement_name || 'N/A'}</Text>
      </Typography.Title>
      <Typography.Title level={5}>
        Project: <Text mark>{evaluations?.project || 'N/A'}</Text>
      </Typography.Title>
      <Table
        columns={columns}
        dataSource={evaluations?.runs || []}
        onChange={handleChange}
        scroll={{ x: 'max-content' }}
      />
    </>
  );
}
