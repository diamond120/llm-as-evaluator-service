import React, { useState, useEffect, useRef } from 'react';
import { Table, Input, Button, Space, Spin, Typography, notification, Select, Empty } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import Highlighter from 'react-highlight-words';
import qs from 'qs';
import { ApiError } from '../../components/api-error/api-error';
import llm_evaluator_api_client from '../../services/llm_evaluator_api_client';
import type {
  Filters,
  OnChange,
  FilterDropdownProps,
  DataIndex,
  TableColumnsType,
  IBatches,
  ErrorData,
  InputRef,
  IEngagement,
} from '../../types';

const { Option } = Select;
const { Title, Text } = Typography;

export default function BatchList() {
  const [filteredInfo, setFilteredInfo] = useState<Filters>({});
  const [loading, setLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [engagementsLoading, setEngagementsLoading] = useState(true);
  const [batches, setBatches] = useState<IBatches[]>([]);
  const [engagements, setEngagements] = useState<IEngagement[]>([]);
  const [selectedEngagement, setSelectedEngagement] = useState<string | null>(() => {
    return localStorage.getItem('selectedEngagement');
  });
  const [selectedEngagementId, setSelectedEngagementId] = useState<string | null>(() => {
    return localStorage.getItem('selectedEngagementId');
  });
  const [error, setError] = useState<ErrorData | null>(null);
  const [searchText, setSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

  const fetchEngagements = async () => {
    try {
      const response = await llm_evaluator_api_client.getAllEngagements(
        localStorage.getItem('token'),
      );

      // Sort engagements by name
      const sortedEngagements = response.data.sort((a, b) => a.name.localeCompare(b.name));
      setEngagements(sortedEngagements);

      // If there's a selectedEngagementId but no selectedEngagement, set it here
      if (selectedEngagementId && !selectedEngagement) {
        const engagement = sortedEngagements.find((eng) => eng.id === selectedEngagementId);
        if (engagement) {
          setSelectedEngagement(engagement.name);
          localStorage.setItem('selectedEngagement', engagement.name);
        }
      }
    } catch (err) {
      notification.error({
        message: 'Error',
        description: 'Failed to fetch engagements',
      });
    } finally {
      setEngagementsLoading(false);
    }
  };

  const fetchBatches = async (filters: Filters = {}) => {
    if (!selectedEngagementId) return;
    //setLoading(true);
    setTableLoading(true);
    try {
      const queryParams = qs.stringify(
        { ...filters, engagement_id: selectedEngagementId },
        { arrayFormat: 'comma' },
      );
      const { result } = await llm_evaluator_api_client.fetchBatches(
        queryParams,
        localStorage.getItem('token'),
      );
      setBatches(result);
      setError(null);
    } catch (err) {
      setError(err);
      notification.error({
        message: 'Error',
        description: err.message,
      });
    } finally {
      setTableLoading(false);
    }
  };

  const handleEngagementChange = (value: string) => {
    const selectedEng = engagements.find((eng) => eng.id === value);
    setSelectedEngagement(selectedEng?.name || null);
    setSelectedEngagementId(value);
    localStorage.setItem('selectedEngagement', selectedEng?.name || '');
    localStorage.setItem('selectedEngagementId', value);
  };
  // Handle table changes (pagination, filters, sorting)
  const handleChange: OnChange = async (pagination, filters, sorter) => {
    setFilteredInfo(filters);
    // Removed the fetchBatches call here to prevent double API calls
  };

  // Search related functions
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

  const getColumnSearchProps = (dataIndex: DataIndex): TableColumnType<IBatches> => ({
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
        ? record[dataIndex]
            .toString()
            .toLowerCase()
            .includes((value as string).toLowerCase())
        : false,
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

  // Initial fetch and setup
  useEffect(() => {
    fetchEngagements();
  }, []);

  useEffect(() => {
    if (selectedEngagementId) {
      fetchBatches();
    }
  }, [selectedEngagementId]);

  if (loading) return <Spin size="large" />;

  if (error) return <ApiError error={error} />;

  const columns: TableColumnsType<IBatches> = [
    {
      title: 'Batch ID',
      dataIndex: 'batch_id',
      key: 'batch_id',
      ellipsis: true,
    },
    {
      title: 'Batch Name',
      dataIndex: 'batch_name',
      key: 'batch_name',
      ellipsis: true,
      ...getColumnSearchProps('batch_name'),
      render: (text, record) => (
        <Link
          to={`/evaluations?batch_name=${encodeURIComponent(record.batch_name)}&engagement_id=${selectedEngagementId}`}
        >
          {text}
        </Link>
      ),
    },

    {
      title: 'Engagement',
      dataIndex: 'engagement',
      key: 'engagement',
      ellipsis: true,
      ...getColumnSearchProps('engagement'),
    },
    {
      title: 'Project',
      dataIndex: 'project',
      key: 'project',
      ellipsis: true,
      ...getColumnSearchProps('project'),
    },
    {
      title: 'Created By',
      dataIndex: 'created_by',
      key: 'created_by',
      ellipsis: true,
      ...getColumnSearchProps('created_by'),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: (a: any, b: any) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      ellipsis: true,
    },
  ];

  return (
    <div style={{ padding: '2px' }}>
      <Title level={2}>Batches</Title>
      <Space direction="vertical" size="middle" style={{ display: 'flex', marginBottom: 16 }}>
        <Text strong>Select an Engagement:</Text>
        <Select
          style={{ width: 300 }}
          placeholder="Choose an engagement"
          onChange={handleEngagementChange}
          loading={engagementsLoading}
          value={selectedEngagement}
        >
          {engagements.map((engagement) => (
            <Option key={engagement.id} value={engagement.id}>
              {engagement.name}
            </Option>
          ))}
        </Select>
      </Space>
      {!selectedEngagement ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Text style={{ fontSize: '16px', color: '#1890ff' }}>
              Please select an engagement to view its batches
            </Text>
          }
        />
      ) : tableLoading ? (
        <Spin size="large" />
      ) : (
        <Table
          columns={columns}
          dataSource={batches}
          onChange={handleChange}
          pagination={{ pageSize: 50, showSizeChanger: true }}
          rowKey="batch_id"
          scroll={{ x: 'max-content' }}
          bordered
          title={() => <Text strong>{selectedEngagement} Batches</Text>}
          footer={() => <Text>Total {batches.length} batches</Text>}
        />
      )}
    </div>
  );
}
