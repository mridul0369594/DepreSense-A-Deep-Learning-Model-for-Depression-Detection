/**
 * API helper for communicating with the DepreSense backend.
 *
 * In development: paths are prefixed with `/api` which Vite's dev-server
 * proxy rewrites to `http://localhost:8000`.
 *
 * In production: VITE_API_BASE_URL points directly to the Cloud Run URL
 * (e.g. https://depresense-backend-xxxxx.run.app).
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export interface ApiError {
    code: string;
    message: string;
}

/**
 * Thin wrapper around `fetch` that:
 * - prepends `API_BASE`
 * - sets JSON headers + Bearer token
 * - throws an `ApiError`-shaped error on non-2xx responses
 */
async function request<T>(
    path: string,
    options: RequestInit = {},
): Promise<T> {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {
        ...(options.headers as Record<string, string>),
    };

    // Only set Content-Type to JSON if body is not FormData
    if (!(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    let res: Response;
    try {
        res = await fetch(`${API_BASE}${path}`, {
            ...options,
            headers,
        });
    } catch (networkErr) {
        // Network error — backend is unreachable or request was blocked
        throw {
            code: "NETWORK_ERROR",
            message: "Unable to connect to the server. Please check that the backend is running and try again.",
        } as ApiError;
    }

    // Safely parse JSON — the response might not be JSON (e.g. proxy error HTML)
    let data: any;
    try {
        data = await res.json();
    } catch {
        // Response body is not valid JSON
        if (!res.ok) {
            throw {
                code: "SERVER_ERROR",
                message: `Server returned an error (${res.status}). Please try again later.`,
            } as ApiError;
        }
        // 2xx but non-JSON body — unusual but handle gracefully
        throw {
            code: "PARSE_ERROR",
            message: "Received an unexpected response from the server.",
        } as ApiError;
    }

    if (!res.ok) {
        // Backend returns  { detail: { code, message } }
        const detail = data?.detail;
        const err: ApiError = {
            code: detail?.code ?? "UNKNOWN_ERROR",
            message: detail?.message ?? data?.detail ?? "Something went wrong.",
        };
        throw err;
    }

    return data as T;
}

// ── Auth types ──────────────────────────────────────────────

export interface LoginSendOtpResponse {
    message: string;
    email: string;
    status: string;
}

export interface UserResponse {
    uid: string;
    email: string;
    name: string | null;
    created_at: string | null;
}

export interface AuthTokenResponse {
    token: string;
    user: UserResponse;
    message: string;
}

// ── Auth API calls ──────────────────────────────────────────

/** Step 1: validate credentials + send OTP email */
export function loginSendOtp(email: string, password: string) {
    return request<LoginSendOtpResponse>("/auth/login-send-otp", {
        method: "POST",
        body: JSON.stringify({ email, password }),
    });
}

/** Step 2: verify OTP + complete login */
export function loginVerifyOtp(
    email: string,
    password: string,
    otp: string,
) {
    return request<AuthTokenResponse>("/auth/login-verify-otp", {
        method: "POST",
        body: JSON.stringify({ email, password, otp }),
    });
}

/** Resend a new OTP to the given email */
export function resendOtp(email: string) {
    return request<{ message: string }>("/auth/resend-otp", {
        method: "POST",
        body: JSON.stringify({ email }),
    });
}

// ── Forgot Password API calls ─────────────────────────────────

/** Step 1: Send OTP to email for password reset */
export function forgotPasswordSendOtp(email: string) {
    return request<{ message: string; email: string; status: string }>(
        "/auth/forgot-password",
        {
            method: "POST",
            body: JSON.stringify({ email }),
        },
    );
}

/** Step 2: Verify OTP for password reset */
export function forgotPasswordVerifyOtp(email: string, otp: string) {
    return request<{
        message: string;
        email: string;
        reset_token: string;
        status: string;
    }>("/auth/forgot-password/verify-otp", {
        method: "POST",
        body: JSON.stringify({ email, otp }),
    });
}

/** Step 3: Reset password after OTP verification */
export function forgotPasswordReset(
    email: string,
    newPassword: string,
    resetToken: string,
) {
    return request<{ message: string; status: string }>(
        "/auth/forgot-password/reset",
        {
            method: "POST",
            body: JSON.stringify({
                email,
                new_password: newPassword,
                reset_token: resetToken,
            }),
        },
    );
}

// ── Change Password API call ──────────────────────────────────

/** Change password for an authenticated user */
export function changePassword(currentPassword: string, newPassword: string) {
    return request<{ message: string }>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
        }),
    });
}

// ── EEG types ──────────────────────────────────────────────

export interface EEGUploadResponse {
    file_id: string;
    filename: string;
    status: string;
    message: string;
    uploaded_at: string;
}

// ── EEG API calls ──────────────────────────────────────────

/** Upload a .edf file to the backend */
export function uploadEEGFile(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    return request<EEGUploadResponse>("/eeg/upload", {
        method: "POST",
        body: formData,
    });
}

// ── Prediction types ───────────────────────────────────────

export interface PredictionResult {
    prediction_id: string;
    depression_probability: number;
    risk_level: string;
    confidence: number;
    timestamp: string;
}

export interface ShapExplanation {
    feature_importance: Record<string, number | { abs_importance: number; signed_importance: number }>;
    top_features: string[];
    base_value: number;
    explanation_summary: string;
    shap_status: string;
}

export interface PredictionResponse {
    result: PredictionResult;
    explanation: ShapExplanation;
    message: string;
}

// ── Prediction API calls ───────────────────────────────────

/** Run depression prediction on an uploaded EEG file */
export function runPrediction(fileId: string) {
    return request<PredictionResponse>("/predictions/predict", {
        method: "POST",
        body: JSON.stringify({ file_id: fileId }),
    });
}

/** Get prediction history for the current user */
export function getPredictionHistory() {
    return request<PredictionResponse[]>("/predictions/history", {
        method: "GET",
    });
}

/** Get a specific prediction by ID */
export function getPrediction(predictionId: string) {
    return request<PredictionResponse>(`/predictions/${predictionId}`, {
        method: "GET",
    });
}

// ── System Status types ────────────────────────────────────

export interface HealthResponse {
    status: string;
    uptime: string;
    version: string;
}

export interface DatabaseStatusResponse {
    firebase_connected: boolean;
    databaseStatus: string;
    uptime: string;
}

export interface ModelStatusResponse {
    model_loaded: boolean;
    modelStatus: string;
    modelVersion: string;
    uptime: string;
}

export interface SystemStatusResponse {
    api: {
        status: string;
        uptime: string;
    };
    database: {
        status: string;
        uptime: string;
    };
    model: {
        status: string;
        uptime: string;
        version: string;
    };
    metrics: {
        totalAnalysesToday: number;
        avgProcessingTime: number;
        modelVersion: string;
    };
}

// ── System Status API calls ────────────────────────────────

/** Get API health status (no auth required) */
export function getHealthStatus() {
    return request<HealthResponse>("/health", { method: "GET" });
}

/** Get database (Firebase) status (no auth required) */
export function getDatabaseStatus() {
    return request<DatabaseStatusResponse>("/health/firebase", { method: "GET" });
}

/** Get ML model status (no auth required) */
export function getModelStatus() {
    return request<ModelStatusResponse>("/health/model", { method: "GET" });
}

/** Get combined system status with clinician-specific metrics (auth required) */
export function getSystemStatus() {
    return request<SystemStatusResponse>("/health/system-status", { method: "GET" });
}

// ── Admin Panel types ──────────────────────────────────────

export interface AdminLoginResponse {
    message: string;
    email: string;
    status: string;
}

export interface AdminOTPResponse {
    token: string;
    user: {
        uid: string;
        email: string;
        name: string;
    };
    message: string;
}

export interface AdminUser {
    id: string;
    full_name: string;
    email: string;
    role: string;
    phone: string | null;
    last_active: string;
    status: string;
}

export interface AdminUserListResponse {
    users: AdminUser[];
}

export interface AdminLogEntry {
    id: string;
    timestamp: string;
    type: string;
    user: string;
    action: string;
    details: string;
}

export interface AdminLogsResponse {
    logs: AdminLogEntry[];
    total_events: number;
    user_logins: number;
    warnings: number;
}

export interface AdminSettings {
    session_timeout: number;
    maintenance_mode: boolean;
    auto_approve: boolean;
    email_notifications: boolean;
}

export interface AdminSettingsResponse {
    settings: AdminSettings;
    message: string;
}

// ── Admin Panel API calls ──────────────────────────────────

/** Admin login: validate hardcoded credentials + send OTP */
export function adminLogin(email: string, password: string) {
    return request<AdminLoginResponse>("/admin/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
    });
}

/** Admin OTP verification */
export function adminVerifyOtp(email: string, otp: string) {
    return request<AdminOTPResponse>("/admin/verify-otp", {
        method: "POST",
        body: JSON.stringify({ email, otp }),
    });
}

/** Get managed users by status */
export function getAdminUsers(statusFilter: string = "Active") {
    return request<AdminUserListResponse>(
        `/admin/users?status_filter=${encodeURIComponent(statusFilter)}`,
        { method: "GET" },
    );
}

/** Add a new user */
export function addAdminUser(data: {
    full_name: string;
    email: string;
    role: string;
    phone?: string;
}) {
    return request<AdminUser>("/admin/users", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

/** Edit an existing user */
export function editAdminUser(userId: string, data: {
    full_name?: string;
    role?: string;
    phone?: string;
    status?: string;
}) {
    return request<AdminUser>(`/admin/users/${userId}`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
}

/** Soft-delete a user (set status to Removed) */
export function deleteAdminUser(userId: string) {
    return request<{ message: string; user_id: string }>(
        `/admin/users/${userId}`,
        { method: "DELETE" },
    );
}

/** Restore a removed user back to Active */
export function restoreAdminUser(userId: string) {
    return request<{ message: string; user_id: string }>(
        `/admin/users/${userId}/restore`,
        { method: "POST" },
    );
}

/** Get system logs */
export function getSystemLogs() {
    return request<AdminLogsResponse>("/admin/logs", { method: "GET" });
}

/** Get admin settings */
export function getAdminSettings() {
    return request<AdminSettingsResponse>("/admin/settings", { method: "GET" });
}

/** Update admin settings */
export function updateAdminSettings(settings: AdminSettings) {
    return request<AdminSettingsResponse>("/admin/settings", {
        method: "PUT",
        body: JSON.stringify(settings),
    });
}

/** Check maintenance mode (public, no auth) */
export function checkMaintenanceStatus() {
    return request<{ maintenance_mode: boolean; message: string }>(
        "/admin/maintenance-status",
        { method: "GET" },
    );
}
