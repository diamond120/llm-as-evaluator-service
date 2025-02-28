import React from 'react';
import { Layout as AntLayout, Menu, Dropdown, Avatar, Typography } from 'antd';
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { UserOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons';
import { useAuth } from '../../context/AuthContext';
import xxxxLogoWhite from '#/assets/xxxx-white.svg';
import SideMenu from './SideMenu';

const { Header, Sider, Content } = AntLayout;
const { Title } = Typography;

// Define page headers
const pageHeaders: { [key: string]: string } = {
  '/': 'LLM Evaluator Service - Batches',
  '/evaluators': 'Evaluators',
  '/evaluations': 'Evaluations',
  '/onboard': 'Onboard New User',
  '/profile': 'User Profile',
  '/cost-tracking': 'Cost Tracking',
  '/api-token': 'API Token Management',
  '/report-download': 'Report Download',
};

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout();
      navigate('/login');
    } else if (key === 'profile') {
      navigate('/profile');
    }
  };

  const userMenu = (
    <Menu onClick={handleMenuClick}>
      <Menu.Item key="profile" icon={<SettingOutlined />}>
        Profile
      </Menu.Item>
      <Menu.Item key="logout" icon={<LogoutOutlined />}>
        Logout
      </Menu.Item>
    </Menu>
  );

  // Get the current page header
  const currentHeader = pageHeaders[location.pathname] || 'LLM Evaluator Service';

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider style={{ backgroundColor: '#1A202C', padding: 24 }} width={250}>
        <Link to="/">
          <img src={xxxxLogoWhite} alt="xxxx Logo" style={{ width: 100, marginBottom: 20 }} />
        </Link>
        <SideMenu />
      </Sider>
      <AntLayout>
        <Header
          style={{
            background: '#fff',
            padding: '0 20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Title level={3} style={{ margin: 0 }}>
            {currentHeader}
          </Title>
          <Dropdown overlay={userMenu} trigger={['click']}>
            <Avatar icon={<UserOutlined />} style={{ cursor: 'pointer' }} />
          </Dropdown>
        </Header>
        <Content style={{ margin: '24px 16px 0' }}>
          <div style={{ padding: 24, background: '#fff', minHeight: 360 }}>
            <Outlet />
          </div>
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
