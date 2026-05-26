/** TypeScript type definitions for authentication. */

export type Role = 'student' | 'instructor' | 'super-admin';

export interface User {
  id: string;
  org_id: string;
  email: string;
  name: string;
  roles: Role[];
  auth_provider: string;
  google_sub: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface UserListResponse {
  users: User[];
  total: number;
  offset: number;
  limit: number;
}

export interface RoleAssignmentRequest {
  role: Role;
}