---
name: api-integration
description: Design and implement robust API integrations with proper error handling, retry logic, type safety, and security. Use when building API clients, handling HTTP requests, or integrating with external services.
---

# API Integration Skill

## Overview

Build production-ready API integrations that handle errors gracefully, provide excellent developer experience, and maintain security and reliability.

## When to Use This Skill

Activate when the user:
- Implements API clients or HTTP requests
- Integrates with external services (Auth0, Stripe, etc.)
- Builds backend-to-backend communication
- Needs to handle API errors and retries
- Implements authentication and authorization
- Works with WebSockets or real-time connections
- Designs API request/response patterns

## Core Principles

### 1. Centralized API Client

Create a configured client instance, don't scatter fetch calls:

```typescript
// ✅ GOOD - Centralized API client
// src/services/api.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor for auth tokens
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Handle token refresh or redirect to login
      await handleUnauthorized();
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### 2. Type-Safe API Service Layer

Create service classes with typed responses:

```typescript
// ✅ GOOD - Typed API service
// src/services/companyService.ts
import apiClient from './api';
import type { Company, CreateCompanyRequest, UpdateCompanyRequest } from '../types';

export class CompanyService {
  private readonly basePath = '/companies';
  
  async getAll(): Promise<Company[]> {
    const response = await apiClient.get<Company[]>(this.basePath);
    return response.data;
  }
  
  async getById(id: string): Promise<Company> {
    const response = await apiClient.get<Company>(`${this.basePath}/${id}`);
    return response.data;
  }
  
  async create(data: CreateCompanyRequest): Promise<Company> {
    const response = await apiClient.post<Company>(this.basePath, data);
    return response.data;
  }
  
  async update(id: string, data: UpdateCompanyRequest): Promise<Company> {
    const response = await apiClient.put<Company>(`${this.basePath}/${id}`, data);
    return response.data;
  }
  
  async delete(id: string): Promise<void> {
    await apiClient.delete(`${this.basePath}/${id}`);
  }
}

export const companyService = new CompanyService();

// ❌ BAD - Scattered fetch calls
function CompanyList() {
  const [companies, setCompanies] = useState([]);
  
  useEffect(() => {
    fetch('http://localhost:8080/api/v1/companies') // Hardcoded URL, no error handling
      .then(res => res.json())
      .then(data => setCompanies(data));
  }, []);
}
```

### 3. Comprehensive Error Handling

Define error types and handle them appropriately:

```typescript
// ✅ GOOD - Structured error handling
// src/types/errors.ts
export class ApiError extends Error {
  constructor(
    public statusCode: number,
    public code: string,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
  
  static fromResponse(error: any): ApiError {
    if (error.response) {
      return new ApiError(
        error.response.status,
        error.response.data.error || 'UNKNOWN_ERROR',
        error.response.data.message || 'An error occurred',
        error.response.data.details
      );
    }
    
    if (error.request) {
      return new ApiError(0, 'NETWORK_ERROR', 'Network request failed');
    }
    
    return new ApiError(0, 'UNKNOWN_ERROR', error.message);
  }
  
  isValidationError(): boolean {
    return this.statusCode === 400 || this.code === 'VALIDATION_ERROR';
  }
  
  isNotFound(): boolean {
    return this.statusCode === 404;
  }
  
  isUnauthorized(): boolean {
    return this.statusCode === 401;
  }
  
  isForbidden(): boolean {
    return this.statusCode === 403;
  }
}

// Usage in service
export class CompanyService {
  async create(data: CreateCompanyRequest): Promise<Company> {
    try {
      const response = await apiClient.post<Company>('/companies', data);
      return response.data;
    } catch (error) {
      throw ApiError.fromResponse(error);
    }
  }
}

// Usage in component
function CreateCompanyForm() {
  const [error, setError] = useState<string | null>(null);
  
  const handleSubmit = async (data: CreateCompanyRequest) => {
    try {
      await companyService.create(data);
      navigate('/companies');
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.isValidationError()) {
          setError(`Validation failed: ${error.message}`);
        } else if (error.isUnauthorized()) {
          navigate('/login');
        } else {
          setError('An unexpected error occurred. Please try again.');
        }
      }
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      {error && <ErrorAlert message={error} />}
      {/* Form fields */}
    </form>
  );
}
```

### 4. Retry Logic with Exponential Backoff

Implement resilient retry strategies:

```typescript
// ✅ GOOD - Retry with exponential backoff
// src/utils/retry.ts
export interface RetryOptions {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  shouldRetry?: (error: any) => boolean;
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions
): Promise<T> {
  const { maxRetries, baseDelay, maxDelay, shouldRetry } = options;
  let lastError: any;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      // Don't retry if we shouldn't or if it's the last attempt
      if (attempt === maxRetries || (shouldRetry && !shouldRetry(error))) {
        throw error;
      }
      
      // Calculate delay with exponential backoff and jitter
      const exponentialDelay = Math.min(baseDelay * Math.pow(2, attempt), maxDelay);
      const jitter = Math.random() * 0.3 * exponentialDelay;
      const delay = exponentialDelay + jitter;
      
      console.log(`Retry attempt ${attempt + 1}/${maxRetries} after ${delay}ms`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError;
}

// Usage
async function fetchCompanies(): Promise<Company[]> {
  return withRetry(
    () => companyService.getAll(),
    {
      maxRetries: 3,
      baseDelay: 1000,
      maxDelay: 10000,
      shouldRetry: (error) => {
        // Only retry on network errors or 5xx server errors
        const apiError = ApiError.fromResponse(error);
        return apiError.statusCode === 0 || apiError.statusCode >= 500;
      }
    }
  );
}
```

### 5. Request Cancellation

Cancel requests when components unmount:

```typescript
// ✅ GOOD - Request cancellation
import { useEffect, useState } from 'react';
import { companyService } from '../services/companyService';

function CompanyList() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const abortController = new AbortController();
    
    async function loadCompanies() {
      try {
        setLoading(true);
        const data = await companyService.getAll({ signal: abortController.signal });
        setCompanies(data);
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Failed to load companies:', error);
        }
      } finally {
        setLoading(false);
      }
    }
    
    loadCompanies();
    
    // Cleanup: cancel request if component unmounts
    return () => abortController.abort();
  }, []);
  
  return <div>{/* Render companies */}</div>;
}

// Update service to accept signal
export class CompanyService {
  async getAll(config?: { signal?: AbortSignal }): Promise<Company[]> {
    const response = await apiClient.get<Company[]>('/companies', config);
    return response.data;
  }
}
```

### 6. React Query Integration (Recommended)

Use React Query for automatic caching, refetching, and state management:

```typescript
// ✅ GOOD - React Query integration
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { companyService } from '../services/companyService';

// Query hooks
export function useCompanies() {
  return useQuery({
    queryKey: ['companies'],
    queryFn: () => companyService.getAll(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)
  });
}

export function useCompany(id: string) {
  return useQuery({
    queryKey: ['companies', id],
    queryFn: () => companyService.getById(id),
    enabled: !!id // Only fetch if id is provided
  });
}

// Mutation hooks
export function useCreateCompany() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateCompanyRequest) => companyService.create(data),
    onSuccess: (newCompany) => {
      // Invalidate companies list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      
      // Or optimistically update cache
      queryClient.setQueryData<Company[]>(['companies'], (old = []) => {
        return [...old, newCompany];
      });
    },
    onError: (error) => {
      console.error('Failed to create company:', error);
      // Show error notification
    }
  });
}

// Usage in component
function CompanyList() {
  const { data: companies, isLoading, error } = useCompanies();
  const createMutation = useCreateCompany();
  
  if (isLoading) return <Spinner />;
  if (error) return <ErrorDisplay error={error} />;
  
  return (
    <div>
      {companies?.map(company => (
        <CompanyCard key={company.id} company={company} />
      ))}
      
      <button
        onClick={() => createMutation.mutate({ name: 'New Company', taxId: '12345678' })}
        disabled={createMutation.isPending}
      >
        {createMutation.isPending ? 'Creating...' : 'Create Company'}
      </button>
    </div>
  );
}
```

### 7. Optimistic Updates

Update UI immediately, rollback on error:

```typescript
// ✅ GOOD - Optimistic updates
export function useUpdateCompany() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateCompanyRequest }) =>
      companyService.update(id, data),
      
    onMutate: async ({ id, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['companies', id] });
      
      // Snapshot previous value
      const previousCompany = queryClient.getQueryData<Company>(['companies', id]);
      
      // Optimistically update
      queryClient.setQueryData<Company>(['companies', id], (old) => ({
        ...old!,
        ...data
      }));
      
      // Return context with snapshot
      return { previousCompany };
    },
    
    onError: (error, variables, context) => {
      // Rollback on error
      if (context?.previousCompany) {
        queryClient.setQueryData(
          ['companies', variables.id],
          context.previousCompany
        );
      }
    },
    
    onSettled: (data, error, variables) => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['companies', variables.id] });
    }
  });
}
```

### 8. File Upload Handling

Handle file uploads with progress tracking:

```typescript
// ✅ GOOD - File upload with progress
export class DocumentService {
  async upload(
    file: File,
    companyId: string,
    onProgress?: (progress: number) => void
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('companyId', companyId);
    
    const response = await apiClient.post<DocumentUploadResponse>(
      '/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress?.(progress);
          }
        }
      }
    );
    
    return response.data;
  }
}

// Usage
function FileUploader({ companyId }: { companyId: string }) {
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    try {
      setUploading(true);
      const result = await documentService.upload(file, companyId, setProgress);
      console.log('Upload successful:', result);
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };
  
  return (
    <div>
      <input type="file" onChange={handleFileChange} disabled={uploading} />
      {uploading && <ProgressBar progress={progress} />}
    </div>
  );
}
```

## Security Best Practices

### 1. Never Expose Secrets in Frontend

```typescript
// ❌ BAD - Secret in frontend code
const API_KEY = 'sk_live_abc123';

// ✅ GOOD - Use environment variables and proxy through backend
const API_URL = import.meta.env.VITE_API_URL; // Public API URL only
// Backend handles API keys and secrets
```

### 2. Validate and Sanitize Input

```typescript
// ✅ GOOD - Input validation
import { z } from 'zod';

const createCompanySchema = z.object({
  name: z.string().min(1).max(100),
  taxId: z.string().regex(/^\d{8,11}$/),
  email: z.string().email()
});

export class CompanyService {
  async create(data: unknown): Promise<Company> {
    // Validate before sending
    const validatedData = createCompanySchema.parse(data);
    const response = await apiClient.post<Company>('/companies', validatedData);
    return response.data;
  }
}
```

### 3. CSRF Protection

```typescript
// ✅ GOOD - CSRF token handling
apiClient.interceptors.request.use((config) => {
  const csrfToken = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content;
  if (csrfToken) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});
```

## Testing API Integrations

```typescript
// Mock API responses in tests
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/v1/companies', (req, res, ctx) => {
    return res(ctx.json([
      { id: '1', name: 'Acme Corp', taxId: '12345678' }
    ]));
  }),
  
  rest.post('/api/v1/companies', async (req, res, ctx) => {
    const body = await req.json();
    return res(ctx.status(201), ctx.json({
      id: '2',
      ...body
    }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('should fetch companies', async () => {
  const companies = await companyService.getAll();
  expect(companies).toHaveLength(1);
  expect(companies[0].name).toBe('Acme Corp');
});
```

## Remember

- Centralize API configuration
- Type all API responses
- Handle errors comprehensively
- Implement retry logic for transient failures
- Cancel requests on unmount
- Use React Query for server state
- Never expose secrets in frontend
- Test with mocked responses
- Log errors for debugging
- Provide user feedback for long operations

