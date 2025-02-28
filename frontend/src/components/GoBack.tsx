// GoBackButton.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import '../assets/css/GoBack.css';

const GoBackButton = ({ style = {}, className = '' }) => {
  const navigate = useNavigate();

  const handleGoBack = () => {
    navigate(-1);
  };

  return (
    <Button
      onClick={handleGoBack}
      type="default"
      size="small"
      icon={<ArrowLeftOutlined />}
      className={`go-back-button ${className}`}
      style={{ ...defaultStyle, ...style }}
    >
      Go Back
    </Button>
  );
};

const defaultStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '100px',
  height: '30px',
  fontSize: '12px',
  fontWeight: 'bold',
  borderRadius: '5px',
};

export default GoBackButton;
