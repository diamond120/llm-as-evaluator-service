import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import '../../assets/css/LLMStyles.css';
import {
  Alert,
  Form,
  Input,
  Select,
  Button,
  notification,
  Divider,
  Typography,
  Steps,
  Descriptions,
} from 'antd';
import llm_evaluator_api_client from '../../services/llm_evaluator_api_client';
import AuthContext from '../../context/AuthContext';

const { Option } = Select;
const { Title } = Typography;
const { Step } = Steps;

const OnboardNewUser = () => {
  const { user } = useContext(AuthContext);
  const token = localStorage.getItem('token');
  const [form] = Form.useForm();
  const [engagements, setEngagements] = useState([]);
  const [projects, setProjects] = useState([]);
  const [roles, setRoles] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState({
    engagements: false,
    projects: false,
    roles: false,
    users: false,
    submit: false,
  });
  const [selectedEngagement, setSelectedEngagement] = useState(null);
  const [selectedProject, setSelectedProject] = useState(null);
  const [selectedRole, setSelectedRole] = useState(null);
  const [isAddingNewUser, setIsAddingNewUser] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [isAddingNewProject, setIsAddingNewProject] = useState(false);
  const [engagementError, setEngagementError] = useState(null);
  const [isAddingNewEngagement, setIsAddingNewEngagement] = useState(false);
  const [tempValues, setTempValues] = useState({});
  const navigate = useNavigate();

  useEffect(() => {
    if (user?.access !== 'superadmin') {
      notification.error({
        message: 'Access Denied',
        description: 'Only superadmins can onboard new users.',
      });
      navigate('/');
    } else {
      fetchEngagements();
    }
  }, [user, navigate]);

  useEffect(() => {
    if (selectedEngagement && !isAddingNewEngagement) {
      fetchProjects(selectedEngagement);
    }
  }, [selectedEngagement, isAddingNewEngagement]);

  useEffect(() => {
    if (selectedProject) {
      fetchRoles();
    }
  }, [selectedProject]);

  useEffect(() => {
    if (selectedRole) {
      fetchUsers();
    }
  }, [selectedRole]);

  const fetchEngagements = async () => {
    setLoading((prev) => ({ ...prev, engagements: true }));
    try {
      const response = await llm_evaluator_api_client.getAllEngagements(token);
      setEngagements(response.data);
    } catch (error) {
      notification.error({ message: 'Error fetching engagements' });
    } finally {
      setLoading((prev) => ({ ...prev, engagements: false }));
    }
  };

  const fetchProjects = async (engagementId) => {
    setLoading((prev) => ({ ...prev, projects: true }));
    try {
      const response = await llm_evaluator_api_client.getProjectsForEngagement(engagementId, token);
      setProjects(response.data);
    } catch (error) {
      notification.error({ message: 'Error fetching projects' });
    } finally {
      setLoading((prev) => ({ ...prev, projects: false }));
    }
  };

  const fetchRoles = async () => {
    setLoading((prev) => ({ ...prev, roles: true }));
    try {
      const response = await llm_evaluator_api_client.getAllRoles(token);
      setRoles(response.data);
    } catch (error) {
      notification.error({ message: 'Error fetching roles' });
    } finally {
      setLoading((prev) => ({ ...prev, roles: false }));
    }
  };

  const fetchUsers = async () => {
    setLoading((prev) => ({ ...prev, users: true }));
    try {
      const response = await llm_evaluator_api_client.getAllUsers(token);
      setUsers(response.data);
    } catch (error) {
      notification.error({ message: 'Error fetching users' });
    } finally {
      setLoading((prev) => ({ ...prev, users: false }));
    }
  };

  const handleNext = async () => {
    try {
      const values = await form.validateFields();
      setTempValues((prev) => ({ ...prev, ...values }));

      if (currentStep === 0) {
        if (isAddingNewEngagement) {
          await handleCreateNewEngagement();
        } else {
          fetchProjects(values.engagementId);
        }
      }
      if (currentStep === 1) fetchRoles();
      if (currentStep === 2) fetchUsers();
      setCurrentStep((prev) => prev + 1);
    } catch (error) {
      console.error('Validation Failed:', error);
    }
  };

  const handleCreateNewEngagement = async () => {
    try {
      setLoading((prev) => ({ ...prev, submit: true }));
      const newEngagementName = form.getFieldValue('newEngagementName');
      const webhookUrl = form.getFieldValue('webhookUrl');
      const authToken = form.getFieldValue('authToken');
      const engagementData = {
        name: newEngagementName,
        webhook_url: webhookUrl,
        auth_token: authToken,
      };
      const response = await llm_evaluator_api_client.createNewEngagement(engagementData, token);
      setEngagements([...engagements, response]);
      form.setFieldsValue({ engagementId: response.id });
      setSelectedEngagement(response.id);
      setIsAddingNewEngagement(false);
      setEngagementError(null);
    } catch (error) {
      setEngagementError('Failed to create new engagement. Please try again.');
      throw error;
    } finally {
      setLoading((prev) => ({ ...prev, submit: false }));
    }
  };

  const handlePrevious = () => {
    setCurrentStep((prev) => prev - 1);
  };

  const handleSubmit = async () => {
    try {
      setLoading((prev) => ({ ...prev, submit: true }));
      const data = {
        engagement_id: tempValues.engagementId,
        project_id: isAddingNewProject ? null : tempValues.projectId,
        new_project_name: isAddingNewProject ? tempValues.newProjectName : null,
        role_id: tempValues.roleId,
        user_id: isAddingNewUser ? null : tempValues.userId,
        new_user_name: isAddingNewUser ? tempValues.newUserName : null,
        new_user_email: isAddingNewUser ? tempValues.newUserEmail : null,
      };
      const response = await llm_evaluator_api_client.onboardUser(data, token);
      notification.success({
        message: 'Success',
        description: (
          <div>
            <p>{response.message} entry</p>
            <p>Engagement: {engagements.find((e) => e.id === tempValues.engagementId)?.name}</p>
            <p>
              Project:{' '}
              {isAddingNewProject
                ? tempValues.newProjectName
                : projects.find((p) => p.id === tempValues.projectId)?.name}
            </p>
            <p>Role: {roles.find((r) => r.id === tempValues.roleId)?.name}</p>
            {isAddingNewUser ? (
              <>
                <p>User Name: {tempValues.newUserName}</p>
                <p>User Email: {tempValues.newUserEmail}</p>
              </>
            ) : (
              <p>User: {users.find((u) => u.id === tempValues.userId)?.email}</p>
            )}
            <p>Token: {response?.token}</p>
            <Button
              type="primary"
              onClick={() => {
                navigator.clipboard.writeText(response?.token);
                notification.success({ message: 'Token copied to clipboard!' });
              }}
            >
              Copy Token to Clipboard
            </Button>
          </div>
        ),
        onClose: () => {
          navigate('/');
        },
      });
    } catch (error) {
      notification.error({ message: 'Onboarding Error', description: error.message });
    } finally {
      setLoading((prev) => ({ ...prev, submit: false }));
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>Onboard New User to Engagement</Title>
      <Steps current={currentStep}>
        <Step title="Engagement" />
        <Step title="Project" />
        <Step title="Role" />
        <Step title="User" />
        <Step title="Review and Submit" />
      </Steps>
      <Form
        form={form}
        layout="vertical"
        onValuesChange={(changedValues, allValues) => {
          if (changedValues.engagementId) {
            setSelectedEngagement(changedValues.engagementId);
            form.setFieldsValue({ projectId: undefined, newProjectName: '' });
            setProjects([]);
            setRoles([]);
            setUsers([]);
            setSelectedProject(null);
            setSelectedRole(null);
          }
          if (changedValues.projectId) {
            setSelectedProject(changedValues.projectId);
            setRoles([]);
            setUsers([]);
            setSelectedRole(null);
          }
          if (changedValues.roleId) {
            setSelectedRole(changedValues.roleId);
            setUsers([]);
          }
        }}
      >
        {currentStep === 0 && (
          <>
            <Divider orientation="left" className="custom-divider">
              Select Engagement
            </Divider>
            <Form.Item
              name="engagementId"
              label="Select Engagement"
              rules={[
                {
                  required: !isAddingNewEngagement,
                  message: 'Please select an engagement or create a new one',
                },
              ]}
            >
              <Select
                placeholder="Select Engagement"
                loading={loading.engagements}
                onChange={(value) => {
                  setIsAddingNewEngagement(value === 'new');
                  if (value !== 'new') {
                    form.setFieldsValue({
                      newEngagementName: undefined,
                      webhookUrl: undefined,
                      authToken: undefined,
                    });
                    setSelectedEngagement(value);
                  }
                }}
              >
                {engagements.map((engagement) => (
                  <Option key={engagement.id} value={engagement.id}>
                    {engagement.name}
                  </Option>
                ))}
                <Option value="new">Add New Engagement</Option>
              </Select>
            </Form.Item>
            {isAddingNewEngagement && (
              <>
                <Form.Item
                  name="newEngagementName"
                  label="New Engagement Name"
                  rules={[{ required: true, message: 'Please enter the new engagement name' }]}
                >
                  <Input placeholder="New engagement name" />
                </Form.Item>
                <Form.Item
                  name="webhookUrl"
                  label="Webhook URL"
                  rules={[
                    { required: false, message: 'Please enter the webhook URL' },
                    { type: 'url', message: 'Please enter a valid URL' },
                  ]}
                >
                  <Input placeholder="https://example.com/webhook" />
                </Form.Item>
                <Form.Item
                  name="authToken"
                  label="Auth Token"
                  rules={[{ required: false, message: 'Please enter the auth token' }]}
                >
                  <Input.Password placeholder="Enter auth token" />
                </Form.Item>
              </>
            )}
            {engagementError && <Alert message={engagementError} type="error" showIcon />}
            <Button
              type="primary"
              onClick={handleNext}
              disabled={!selectedEngagement && !isAddingNewEngagement}
              style={{ marginLeft: '8px' }}
            >
              Next
            </Button>
          </>
        )}

        {currentStep === 1 && (
          <>
            <Divider orientation="left" className="custom-divider" dashed={true}>
              Create or Select Project
            </Divider>
            <Form.Item
              name="projectId"
              label="Select / Create Project"
              rules={[{ required: true, message: 'Please select a project' }]}
              help="select a project, choose 'Add New Project' for project creation"
            >
              <Select
                placeholder="Select Project"
                loading={loading.projects}
                onChange={(value) => setIsAddingNewProject(value === 'new')}
              >
                {projects.map((project) => (
                  <Option key={project.id} value={project.id}>
                    {project.name}
                  </Option>
                ))}
                <Option value="new">Add New Project</Option>
              </Select>
            </Form.Item>
            {isAddingNewProject && (
              <Form.Item
                name="newProjectName"
                label="New Project Name"
                rules={[{ required: true, message: 'Please enter the new project name' }]}
              >
                <Input placeholder="New project name" />
              </Form.Item>
            )}
            <Button type="primary" onClick={handlePrevious}>
              Previous
            </Button>
            <Button
              type="primary"
              onClick={handleNext}
              style={{ marginLeft: '8px' }}
              disabled={!selectedProject && !isAddingNewProject}
            >
              Next
            </Button>
          </>
        )}

        {currentStep === 2 && (
          <>
            <Divider orientation="left" className="custom-divider">
              Select Role
            </Divider>
            <Form.Item
              name="roleId"
              label="Role"
              rules={[{ required: true, message: 'Please select a role' }]}
            >
              <Select placeholder="Select Role" loading={loading.roles}>
                {roles.map((role) => (
                  <Option key={role.id} value={role.id}>
                    {role.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Button type="primary" onClick={handlePrevious}>
              Previous
            </Button>
            <Button
              type="primary"
              onClick={handleNext}
              disabled={!selectedRole}
              style={{ marginLeft: '8px' }}
            >
              Next
            </Button>
          </>
        )}

        {currentStep === 3 && (
          <>
            <Divider orientation="left" className="custom-divider">
              Create or Select User
            </Divider>
            <Form.Item
              label="User"
              name="userId"
              help="For creating a new user, choose 'Add New User'"
            >
              <Select
                placeholder="Select User"
                loading={loading.users}
                allowClear
                onChange={(value) => setIsAddingNewUser(value === 'new')}
              >
                {users.map((user) => (
                  <Option key={user.id} value={user.id}>
                    {user.email}
                  </Option>
                ))}
                <Option value="new">Add New User</Option>
              </Select>
            </Form.Item>

            {isAddingNewUser && (
              <>
                <Form.Item
                  name="newUserName"
                  label="New User Name"
                  rules={[{ required: true, message: 'Please enter the new user name' }]}
                >
                  <Input placeholder="New user name" />
                </Form.Item>
                <Form.Item
                  name="newUserEmail"
                  label="New User Email"
                  rules={[{ required: true, message: 'Please enter the new user email' }]}
                >
                  <Input placeholder="New user email" />
                </Form.Item>
              </>
            )}
            <Button type="primary" onClick={handlePrevious}>
              Previous
            </Button>

            <Button
              type="primary"
              style={{ marginLeft: '8px' }}
              onClick={handleNext}
              disabled={
                isAddingNewUser
                  ? !form.getFieldValue('newUserName') || !form.getFieldValue('newUserEmail')
                  : false
              }
            >
              Next
            </Button>
          </>
        )}

        {currentStep === 4 && (
          <>
            <Divider orientation="left" className="custom-divider">
              Review and Submit
            </Divider>
            <Descriptions bordered layout="vertical" column={1}>
              <Descriptions.Item label="Engagement">
                {engagements.find((e) => e.id === tempValues.engagementId)?.name}
              </Descriptions.Item>
              <Descriptions.Item label="Project">
                {isAddingNewProject
                  ? tempValues.newProjectName
                  : projects.find((p) => p.id === tempValues.projectId)?.name}
              </Descriptions.Item>
              <Descriptions.Item label="Role">
                {roles.find((r) => r.id === tempValues.roleId)?.name}
              </Descriptions.Item>
              {isAddingNewUser ? (
                <>
                  <Descriptions.Item label="User Name">{tempValues.newUserName}</Descriptions.Item>
                  <Descriptions.Item label="User Email">
                    {tempValues.newUserEmail}
                  </Descriptions.Item>
                </>
              ) : (
                <Descriptions.Item label="User">
                  {users.find((u) => u.id === tempValues.userId)?.email}
                </Descriptions.Item>
              )}
            </Descriptions>
            <Button type="primary" onClick={handlePrevious} style={{ margin: '8px' }}>
              Previous
            </Button>
            <Button
              type="primary"
              onClick={handleSubmit}
              style={{ marginLeft: '8px' }}
              loading={loading.submit}
            >
              Submit
            </Button>
          </>
        )}
      </Form>
    </div>
  );
};

export default OnboardNewUser;
