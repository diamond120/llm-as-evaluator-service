import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Button, message, Typography, Space, Select, Input } from 'antd';
import llm_evaluator_api_client from '../../services/llm_evaluator_api_client';

const { Title, Paragraph } = Typography;
const { Option } = Select;

interface User {
  id: string;
  email: string;
  access: string;
}

const Profile: React.FC = () => {
  const { user } = useAuth();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [clientId, setClientId] = useState<string | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);

  const isSuperAdmin = user.access === 'superadmin';

  useEffect(() => {
    if (isSuperAdmin) {
      fetchUsers();
    }
  }, [isSuperAdmin]);

  const fetchUsers = async () => {
    try {
      const response = await llm_evaluator_api_client.getAllUsers(localStorage.getItem('token'));
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to fetch users', error);
      message.error('Failed to fetch users');
    }
  };

  const handleGetNewAccessToken = async () => {
    try {
      const { token } = await llm_evaluator_api_client.generateToken(
        isSuperAdmin ? selectedUser || user.user_email : user.user_email,
        localStorage.getItem('token'),
      );
      setAccessToken(token);
      message.success('Access token retrieved successfully');
    } catch (error) {
      console.error('Failed to get access token', error);
      message.error('Failed to retrieve access token');
    }
  };

  const handleGenerateClientCredentials = async () => {
    if (!isSuperAdmin) {
      message.error('You do not have permission to generate client credentials');
      return;
    }
    if (!isSuperAdmin) {
      message.error('You do not have permission to generate client credentials');
      return;
    }
    try {
      const { client_id, client_secret } = await llm_evaluator_api_client.generateClientCredentials(
        selectedUser || user.user_email,
        localStorage.getItem('token'),
      );
      setClientId(client_id);
      setClientSecret(client_secret);
      message.success('Client credentials generated successfully');
    } catch (error) {
      console.error('Failed to generate client credentials', error);
      message.error('Failed to generate client credentials');
    }
  };

  const handleCopyToClipboard = (text: string, successMessage: string) => {
    navigator.clipboard.writeText(text);
    message.success(successMessage);
  };

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', padding: '20px' }}>
      <Title level={2}>User Management</Title>
      <Paragraph>
        <strong>Current User Email:</strong> {user.user_email}
      </Paragraph>
      <Paragraph>
        <strong>Current User Role Access:</strong> {user.access}
      </Paragraph>

      {isSuperAdmin && (
        <Select
          style={{ width: 300 }}
          placeholder="Select a user"
          onChange={(value) => setSelectedUser(value)}
          showSearch
          optionFilterProp="children"
        >
          {users.map((user) => (
            <Option key={user.id} value={user.email}>
              {user.email}
            </Option>
          ))}
        </Select>
      )}

      <Space>
        <Button type="primary" onClick={handleGetNewAccessToken}>
          Generate New API Token
        </Button>
        {isSuperAdmin && (
          <Button onClick={handleGenerateClientCredentials}>Generate Client Credentials</Button>
        )}
      </Space>

      {accessToken && (
        <div>
          <Paragraph>
            <strong>API Token (expiry: 30 days):</strong> {accessToken}
          </Paragraph>
          <Button
            onClick={() => handleCopyToClipboard(accessToken, 'API Token copied to clipboard')}
          >
            Copy API Token
          </Button>
        </div>
      )}

      {clientId && clientSecret && (
        <div>
          <Paragraph>
            <strong>Client ID:</strong> {clientId}
          </Paragraph>
          <Paragraph>
            <strong>Client Secret:</strong> {clientSecret}
          </Paragraph>
          <Space>
            <Button
              onClick={() => handleCopyToClipboard(clientId, 'Client ID copied to clipboard')}
            >
              Copy Client ID
            </Button>
            <Button
              onClick={() =>
                handleCopyToClipboard(clientSecret, 'Client Secret copied to clipboard')
              }
            >
              Copy Client Secret
            </Button>
          </Space>
        </div>
      )}
    </Space>
  );
};

export default Profile;
