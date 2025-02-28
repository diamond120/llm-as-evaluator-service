import axios from 'axios';
import { config } from './config';

const BASE_URL = config.evaluatorBaseUrl;
const VITE_API_HOST = config.apiUrl;

class LLMEvaluatorApiService {
  constructor() {
    this.client = axios.create({
      baseURL: BASE_URL,
    });
    this.baseClient = axios.create({
      baseURL: VITE_API_HOST,
    });
  }
  async fetchEvaluatorByName(evaluatorName: string, token: any) {
    try {
      const response = await this.client.get(`/evaluators/${evaluatorName}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Error fetching data from ${`/evaluator/${evaluatorName}`}: ${error.message}`);
    }
  }

  async fetchAllEvaluators(opts: any, token: any) {
    try {
      const response = await this.client.get(`/evaluators/?${opts}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Error fetching data from ${`/evaluators/`}: ${error.message}`);
    }
  }

  async updateEvaluator(name: string, data, token: any) {
    try {
      const response = await this.client.put(`/evaluators/${name}`, data, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Error updating data to ${`/evaluators/${name}`}: ${error.message}`);
    }
  }

  async fetchAllEvaluatorTypes(token: any) {
    try {
      const response = await this.client.get(`/evaluator-types/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Error fetching evaluator types: ${error.message}`);
    }
  }

  async createEvaluator(data, token: any) {
    try {
      const response = await this.client.post(`/evaluators/`, data, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Error creating evaluator: ${error.message}`);
    }
  }

  async createEvaluatorFromCopy(data, token: any) {
    try {
      const response = await this.client.post(`/evaluators/copy/`, data, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Error creating evaluator from copy: ${error.message}`);
    }
  }

  async fetchAllEvaluations(token: any) {
    try {
      const response = await this.client.get(`/evaluations/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Error fetching evaluations: ${error.message}`);
    }
  }
  async filterEvaluations(opts, token: any) {
    try {
      const response = await this.client.get(`/evaluations/?${opts}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      return { result: [] };
      // throw new Error(`Error fetching evaluations: ${error.message}`);
    }
  }
  async fetchEvaluationById(id: number, token: any) {
    try {
      const response = await this.client.get(`/evaluations/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Error fetching evaluation by id: ${error.message}`);
    }
  }
  async fetchBatches(opts: any, token: any) {
    try {
      const response = await this.client.get(`/batches/?${opts}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      console.log(`Response: ${JSON.stringify(response.data)}`);
      return { result: response.data }; // Accessing the nested 'data' property based on the logged structure
    } catch (error) {
      throw new Error(`Error fetching Batches list: ${error.message}`);
    }
  }
  async fetchBatchRuns(opts: any, token: any) {
    try {
      const response = await this.client.get(`/batch/runs/?${opts}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return { result: response.data }; // Accessing the nested 'data' property based on the logged structure
    } catch (error: any) {
      throw new Error(`Error fetching Batch runs: ${error.message}`);
    }
  }
  async fetchBatchEvaluations(opts: any, token: any) {
    try {
      const response = await this.client.get(`/batches/evaluation/?${opts}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return { result: response.data }; // Accessing the nested 'data' property based on the logged structure
    } catch (error: any) {
      throw new Error(`Error fetching Batches list: ${error.message}`);
    }
  }

  async generateClientCredentials(email: string, token: string | null) {
    try {
      const response = await this.baseClient.post(`/v1/a/generate-client-credentials/?email=${encodeURIComponent(email)}`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to generate client credentials: ${error.message}`);
    }
  }
  async generateToken(email: string, token: string | null) {
    try {
      const response = await this.baseClient.post(`/v1/a/generate-token/?email=${encodeURIComponent(email)}&sendTokenByEmail=false`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to call with token: ${error.message}`);
    }
  }
  async getAllEngagements(token: string | null) {
    try {
      const response = await this.baseClient.get('/v1/admin-crud-for-all/engagements',{
      headers: {
        Authorization: `Bearer ${token}`,
      }});
      return response;
    } catch (error) {
      throw new Error(`Error fetching engagements: ${error.message}`);
    }
  }
  async getAllRoles(token: string | null) {
    try {
      const response = await this.baseClient.get('/v1/admin-crud-for-all/roles',{
      headers: {
        Authorization: `Bearer ${token}`,
      }});
      return response;
    } catch (error) {
      throw new Error(`Error fetching roles: ${error.message}`);
    }
  }
  async getAllUsers(token: string | null) {
    try {
      const response = await this.baseClient.get('/v1/admin-crud-for-all/users',{
      headers: {
        Authorization: `Bearer ${token}`,
      }});
      return response;
    } catch (error) {
      throw new Error(`Error fetching users: ${error.message}`);
    }
  }
async getProjectsForEngagement(engagementId: number, token: string | null) {
  try {
    const response = await this.baseClient.get(`/v1/e/projects/${engagementId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response;
  } catch (error) {
    throw new Error(`Error fetching projects for engagement: ${error.message}`);
  }
}
async onboardUser(data: any, token: string | null) {
  try {
    const response = await this.baseClient.post('/v1/admin-crud-for-all/onboard', data, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error(`Error onboarding user: ${JSON.stringify(error.message)}`);
  }
}

async createNewEngagement(data: any, token: string | null) {
  try {
    const response = await this.baseClient.post('/v1/admin-crud-for-all/engagements/', data, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error(`Error creating new engagement: ${JSON.stringify(error.message)}`);
  }
}

async getTokenUsageData(engagement: string, startDate: string, endDate: string, project: string | null, token: string | null) {
  try {
    const response = await this.baseClient.get(`/v1/pricing/token-usage`, {
      params: {
        engagement_id: engagement,
        project_id: project,
        start: startDate,
        end: endDate,
      },
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response;
  } catch (error) {
    throw new Error(`Error fetching token usage data: ${error.message}`);
  }
}


}

export default new LLMEvaluatorApiService();