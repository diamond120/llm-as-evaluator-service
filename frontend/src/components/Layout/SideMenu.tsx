import React from 'react';
import { Menu } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import {
  HomeOutlined,
  AppstoreOutlined,
  FileTextOutlined,
  SettingOutlined,
  UserAddOutlined,
  LineChartOutlined,
  ApiOutlined,
  DownloadOutlined,
} from '@ant-design/icons';

const { SubMenu } = Menu;

const menuItems = [
  {
    key: '/',
    icon: <HomeOutlined />,
    label: <Link to="/">Batches</Link>,
  },
  {
    key: '/evaluators',
    icon: <AppstoreOutlined />,
    label: <Link to="/evaluators">Evaluators</Link>,
  },

  {
    key: '/evaluators/create',
    icon: <FileTextOutlined />,
    label: <Link to="/evaluators/create">Create Evaluator</Link>,
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: 'Settings',
    children: [
      {
        key: '/onboard',
        icon: <UserAddOutlined />,
        label: <Link to="/onboard">Onboard User</Link>,
      },
      {
        key: '/api-token',
        icon: <ApiOutlined />,
        label: <Link to="/api-token">API Token</Link>,
      },
      {
        key: '/cost-tracking',
        icon: <LineChartOutlined />,
        label: <Link to="/cost-tracking">Cost Usage</Link>,
      },

      {
        key: '/report-download',
        icon: <DownloadOutlined />,
        label: <Link to="/report-download">Reports</Link>,
      },
    ],
  },
];

const SideMenu: React.FC = () => {
  const location = useLocation();

  const renderMenuItems = (items: typeof menuItems) => {
    return items.map((item) => {
      if (item.children) {
        return (
          <SubMenu key={item.key} icon={item.icon} title={item.label}>
            {renderMenuItems(item.children)}
          </SubMenu>
        );
      }
      return (
        <Menu.Item key={item.key} icon={item.icon}>
          {item.label}
        </Menu.Item>
      );
    });
  };

  return (
    <Menu
      theme="dark"
      mode="inline"
      selectedKeys={[location.pathname]}
      defaultOpenKeys={['settings']}
      style={{ backgroundColor: 'transparent' }}
    >
      {renderMenuItems(menuItems)}
    </Menu>
  );
};

export default SideMenu;
