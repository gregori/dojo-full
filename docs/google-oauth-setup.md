# Google OAuth Setup Guide

This guide explains how to set up Google OAuth for the Dojo Manager application.

## Prerequisites

- A Google Cloud Platform account
- A project in Google Cloud Console

## Steps

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID

### 2. Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type (unless you have a Google Workspace)
3. Fill in the required fields:
   - App name: "Dojo Manager"
   - User support email: your email
   - Developer contact email: your email
4. Add scopes:
   - `email` (required)
   - `profile` (required)
5. Add test users if in testing mode
6. Save and continue

### 3. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Web application**
4. Name: "Dojo Manager"
5. Add **Authorized redirect URIs**:
   - Development: `http://localhost:8000/api/v1/auth/google/callback`
   - Production: `https://your-domain.com/api/v1/auth/google/callback`
6. Click **Create**
7. Note the **Client ID** and **Client Secret**

### 4. Configure Environment Variables

#### Development (backend/.env)

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

#### Production (Kubernetes Secret)

```bash
kubectl create secret generic backend-secret \
  --namespace=dojo \
  --from-literal=GOOGLE_CLIENT_ID=your-client-id \
  --from-literal=GOOGLE_CLIENT_SECRET=your-client-secret \
  --from-literal=GOOGLE_REDIRECT_URI=https://your-domain.com/api/v1/auth/google/callback
```

### 5. OAuth Flow

The application uses the Authorization Code flow:

1. User clicks "Sign in with Google" on the frontend
2. Frontend redirects to `GET /api/v1/auth/google`
3. Backend generates a CSRF state token, stores it in an httpOnly cookie
4. Backend redirects (302) to Google's OAuth consent screen
5. User consents on Google
6. Google redirects to `GET /api/v1/auth/google/callback?code=...&state=...`
7. Backend validates the CSRF state against the cookie
8. Backend exchanges the authorization code for an ID token
9. Backend verifies the ID token (validates audience = client ID)
10. Backend finds or creates the user
11. Backend sets httpOnly cookies (access_token + refresh_token)
12. Backend redirects (302) to frontend: `/auth/callback?success=true`
13. Frontend calls `GET /api/v1/auth/me` to get user profile

## Security Notes

- The CSRF state token is stored in an httpOnly cookie to prevent XSS
- The Google client secret is never exposed to the frontend
- The ID token is verified server-side using `google-auth` library
- Both access and refresh tokens are stored in httpOnly cookies (not localStorage)
- The `aud` claim in the ID token is verified against the configured client ID