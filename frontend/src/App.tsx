import loadable from '@loadable/component';
import { ConfigProvider, theme } from 'antd';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import './App.css';
import Evaluation from './components/Evaluation';
import Evaluator from './components/Evaluator';
import CreateEvaluator from './components/Evaluator/CreateEvaluator';
import Layout from './components/Layout';

import { AuthProvider } from './context/AuthContext';
import BatchList from './pages/Batch/BatchList';
import RunList from './pages/Batch/RunList';
import EvaluationDetail from './pages/Evaluation/EvaluationDetail';
import Login from './pages/Login/Login';
import ProtectedRoute from './pages/Login/ProtectedRoute';
import Profile from './pages/User';
import OnboardNewUser from './pages/User/OnboardUser';
import ErrorBoundary from './components/ErrorBoundary';
import InProgress from './components/InProgress';
import TokenUsageDashboard from './pages/CostTracking';

const Home = loadable(() => import('#/pages/Evaluator'));

const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },

  {
    path: '/',
    element: <Layout />,
    children: [
      {
        path: '/',
        element: (
          <ProtectedRoute>
            <BatchList />
          </ProtectedRoute>
        ),
      },
      {
        path: '/evaluations',
        element: (
          <ProtectedRoute>
            <RunList />
          </ProtectedRoute>
        ),
      },
      {
        path: '/evaluations/:evaluationId',
        element: <Evaluation />,
      },
      {
        path: '/batches/evaluations',
        element: (
          <ProtectedRoute>
            <EvaluationDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: '/evaluators',
        element: (
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        ),
      },
      {
        path: '/evaluators/:evaluatorName',
        element: (
          <ProtectedRoute>
            <Evaluator />
          </ProtectedRoute>
        ),
      },
      {
        path: '/evaluators/create',
        element: (
          <ProtectedRoute>
            <CreateEvaluator />
          </ProtectedRoute>
        ),
      },
      {
        path: '/profile',
        element: (
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        ),
      },
      {
        path: '/onboard',
        element: (
          <ProtectedRoute>
            <OnboardNewUser />
          </ProtectedRoute>
        ),
      },
      {
        path: '/cost-tracking',
        element: (
          <ProtectedRoute>
            <TokenUsageDashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: '/api-token',
        element: (
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        ),
      },
      {
        path: '/report-download',
        element: (
          <ProtectedRoute>
            <InProgress feature="Report Download" />
          </ProtectedRoute>
        ),
      },
    ],
  },
]);

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
      }}
    >
      <ErrorBoundary>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </ErrorBoundary>
    </ConfigProvider>
  );
}

export default App;
