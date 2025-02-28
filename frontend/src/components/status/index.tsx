import { Tag } from 'antd';

const StatusTag = ({ status }) => {
  let color = '';
  switch (status) {
    case 'pending':
      color = 'orange';
      break;
    case 'success':
      color = 'green';
      break;
    case 'failed':
      color = 'red';
      break;
    case 'queued':
      color = 'yellow';
      break;
    // Add more cases for other statuses as needed
    default:
      color = 'default';
  }

  return <Tag color={color}>{status}</Tag>;
};

export default StatusTag;