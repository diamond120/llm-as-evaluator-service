import React, { useEffect } from 'react';
import { Button, Col, Flex, Image, Row, Typography } from 'antd';
import { Link, useLocation, Outlet } from 'react-router-dom';
import xxxxLogoWhite from '../../assets/xxxx-white.svg';
import googleIcon from '../../assets/images/google.svg';
import { useAuth } from '../../context/AuthContext';
import { config } from '../../services/config';

const Login: React.FC = () => {
  const { login } = useAuth();
  const location = useLocation();
  const apiUrl = config.apiUrl;

  return (
    <Row style={{ width: '100%' }} gutter={0}>
      <Col
        style={{ backgroundColor: '#1A202C', minHeight: '100vh', padding: 24, color: '#ffffff' }}
        span={4}
      >
        <Link to={'/'}>
          <Image preview={false} src={xxxxLogoWhite} style={{ width: 100 }} />
        </Link>
      </Col>
      <Col span={20} style={{ padding: 20 }}>
        <Typography.Title level={1} style={{ margin: 0 }}>
          LLM Evaluator Service
        </Typography.Title>
        <Flex style={{ justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
          <Button
            type="primary"
            block
            size="large"
            onClick={() => (window.location.href = `${apiUrl}/v1/a/auth/login`)}
            icon={
              <img
                src={googleIcon}
                alt="Google"
                style={{ marginRight: 8, width: 20, height: 20 }}
              />
            }
            style={{ textAlign: 'center', width: '300px', height: '50px', fontSize: '18px' }}
          >
            Sign in with Google
          </Button>
        </Flex>
      </Col>
      <Col span={20} style={{ padding: 20 }}>
        <Outlet />
      </Col>
    </Row>
  );
};

export default Login;
