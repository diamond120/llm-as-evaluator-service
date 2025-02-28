import type { CSSProperties } from 'react';
import { CollapseProps, Space, Typography } from 'antd';
import { Collapse } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import { MinusOutlined, PlusOutlined } from '@ant-design/icons';

// Define styles for the menu title
const titleStyle: CSSProperties = {
  fontSize: 18, // Reduced font size for better hierarchy
  fontWeight: 600,
  color: '#ffffff',
  marginBottom: 8, // Added margin for spacing
};

// Define styles for menu items
const itemStyle: CSSProperties = {
  fontSize: 14,
  fontWeight: 400, // Lighter font weight for contrast
  padding: '8px 0',
  color: '#d1d1d1',
  borderRadius: 4, // Subtle rounded corners
  transition: 'background-color 0.2s', // Smooth hover transition
  textDecoration: 'none', // Remove underline from links
};

// Define styles for active menu items
const activeItemStyle: CSSProperties = {
  ...itemStyle,
  backgroundColor: 'rgba(255, 255, 255, 0.1)', // Subtle highlight for active item
};

const menu = [
  {
    title: 'Batches',
    key: 'batches',
    children: [{ title: 'Batches List', path: '/' }],
  },
  {
    title: 'Evaluators',
    key: 'evaluators',
    children: [
      { title: 'Evaluators List', path: '/evaluators' },
      { title: 'Create Evaluator', path: '/evaluators/create' },
    ],
  },
  // {
  //   title: 'Evaluations',
  //   key: 'evaluations',
  //   children: [
  //     { title: 'All Evaluations', path: '/evaluations/?autoRefresh=false' },
  //     { title: 'User Evaluations', path: '/evaluations/?autoRefresh=true' },
  //     { title: 'Create Run', path: '/createRun' }
  //   ],
  // },
  {
    title: 'User Settings',
    key: 'profile',
    children: [
      { title: 'Onboard User', path: '/onboard' },
      { title: 'Get API Token', path: '/profile' },
    ],
  },
];

const useGetMenuItems = (): CollapseProps['items'] => {
  const location = useLocation();

  return menu.map((item) => {
    return {
      label: <Typography.Text style={titleStyle}>{item.title}</Typography.Text>,
      key: item.key,
      showArrow: true,
      style: { border: 'none', marginBottom: 16 },
      children: (
        <Space direction="vertical" style={{ width: '100%' }}>
          {item.children.map((child) => {
            const isActive = location.pathname === child.path;
            return (
              <Link
                to={child.path}
                key={child.title}
                style={isActive ? activeItemStyle : { ...itemStyle }}
              >
                <Typography.Text style={isActive ? activeItemStyle : { ...itemStyle }}>
                  {child.title}
                </Typography.Text>
              </Link>
            );
          })}
        </Space>
      ),
    };
  });
};

export default function Menu() {
  const items = useGetMenuItems();
  return (
    <Collapse
      defaultActiveKey={['batches']}
      bordered={false}
      style={{ background: 'transparent', marginTop: 24 }}
      ghost={true}
      expandIconPosition="right"
      items={items}
      expandIcon={({ isActive }) =>
        isActive ? (
          <MinusOutlined style={{ color: 'white' }} />
        ) : (
          <PlusOutlined style={{ color: 'white' }} />
        )
      }
    />
  );
}
